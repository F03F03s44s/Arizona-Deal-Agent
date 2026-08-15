"""FastAPI application exposing the Arizona Deal Agent."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .agent import rank_deals
from .alerts import (
    check_saved_searches,
    create_saved_search,
    delete_saved_search,
    list_saved_searches,
)
from .data import DEFAULT_BUDGET, load_deals
from .models import (
    AlertCheckResponse,
    RankRequest,
    RankResponse,
    SavedSearch,
    SavedSearchCreate,
    SavedSearchListResponse,
)

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent / "static"

ALERT_INTERVAL_SECONDS = int(os.getenv("ALERT_CHECK_INTERVAL_SECONDS", "300"))


async def _alert_loop(stop: asyncio.Event) -> None:
    """Periodically evaluate saved searches against fresh Craigslist deals."""
    # Stagger the first check so startup scrape finishes first.
    try:
        await asyncio.wait_for(stop.wait(), timeout=15)
        return
    except asyncio.TimeoutError:
        pass

    while not stop.is_set():
        try:
            result = await asyncio.to_thread(check_saved_searches, refresh=True)
            logger.info(
                "Saved-search check: checked=%s alerts=%s",
                result.checked,
                result.alerts_sent,
            )
        except Exception:
            logger.exception("Saved-search background check failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=ALERT_INTERVAL_SECONDS)
            return
        except asyncio.TimeoutError:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = asyncio.Event()
    task = asyncio.create_task(_alert_loop(stop))
    try:
        yield
    finally:
        stop.set()
        await task


app = FastAPI(
    title="Arizona Deal Agent",
    description="Ranks Phoenix Craigslist deals by profitability and affordability.",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/deals")
def list_deals(refresh: bool = False, query: str | None = None) -> dict[str, object]:
    """Return live Phoenix Craigslist deals (sample fallback if scrape fails)."""
    deals, source = load_deals(query=query, refresh=refresh)
    return {
        "budget": DEFAULT_BUDGET,
        "source": source,
        "deals": [d.model_dump() for d in deals],
    }


@app.post("/api/rank", response_model=RankResponse)
def rank(request: RankRequest) -> RankResponse:
    """Rank caller-provided deals, or live Craigslist inventory when empty."""
    if request.deals:
        deals = request.deals
        source = "request"
    else:
        deals, source = load_deals(query=request.query, refresh=request.refresh)

    result = rank_deals(deals, request.budget, request.profit_weight)
    return RankResponse(
        budget=result.budget,
        profit_weight=result.profit_weight,
        ranked=result.ranked,
        recommendation=result.recommendation,
        source=source,
        scraped_count=len(deals),
    )


@app.get("/api/saved-searches", response_model=SavedSearchListResponse)
def get_saved_searches() -> SavedSearchListResponse:
    return SavedSearchListResponse(searches=list_saved_searches())


@app.post("/api/saved-searches", response_model=SavedSearch)
def post_saved_search(payload: SavedSearchCreate) -> SavedSearch:
    return create_saved_search(payload)


@app.delete("/api/saved-searches/{search_id}")
def remove_saved_search(search_id: str) -> dict[str, bool]:
    if not delete_saved_search(search_id):
        raise HTTPException(status_code=404, detail="Saved search not found")
    return {"deleted": True}


@app.post("/api/saved-searches/check", response_model=AlertCheckResponse)
def run_saved_search_check(refresh: bool = True) -> AlertCheckResponse:
    """Manually evaluate saved searches and send any high-score emails."""
    return check_saved_searches(refresh=refresh)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
