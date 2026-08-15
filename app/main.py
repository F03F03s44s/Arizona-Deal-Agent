"""FastAPI application exposing the Arizona Deal Agent."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .agent import rank_deals
from .data import DEFAULT_BUDGET, DEFAULT_QUERY
from .deals import deal_service
from .models import DealsResponse, RankRequest, RankResponse

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Arizona Deal Agent",
    description="Scrapes Phoenix Craigslist and ranks listings by profitability and affordability.",
    version=__version__,
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/deals", response_model=DealsResponse)
def list_deals(
    query: str = Query(default=DEFAULT_QUERY, description="Craigslist search terms."),
    refresh: bool = Query(default=False, description="Bypass the scrape cache."),
) -> DealsResponse:
    """Scrape (or serve from cache) Phoenix listings for a search."""
    sourced = deal_service.get_deals(query, refresh=refresh)
    return DealsResponse(
        budget=DEFAULT_BUDGET,
        query=sourced.query,
        source=sourced.source,
        deals=sourced.deals,
        warning=sourced.warning,
    )


@app.post("/api/rank", response_model=RankResponse)
def rank(request: RankRequest) -> RankResponse:
    """Rank deals against a budget.

    Caller-supplied deals win; otherwise the cached scrape for ``query`` is
    used, which keeps repeated calls off the network.
    """
    if request.deals:
        ranked = rank_deals(request.deals, request.budget, request.profit_weight)
        return ranked.model_copy(update={"source": "request", "query": request.query})

    sourced = deal_service.get_deals(request.query)
    ranked = rank_deals(sourced.deals, request.budget, request.profit_weight)
    return ranked.model_copy(
        update={
            "source": sourced.source,
            "query": sourced.query,
            "warning": sourced.warning,
        }
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
