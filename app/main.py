"""FastAPI application exposing the Arizona Deal Agent."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .agent import rank_deals
from .alerts import AlertService, SavedSearchStore
from .data import DEFAULT_BUDGET, DEFAULT_QUERY
from .deals import deal_service
from .models import (
    Alert,
    DealsResponse,
    RankRequest,
    RankResponse,
    SavedSearch,
    SavedSearchCreate,
    SavedSearchRunResult,
    SourceInfo,
    TopicInfo,
)
from .topics import get_topic, page_slugs, source_infos, topic_infos

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
# Not "data/": that directory holds the CLI's sample listings, which are
# tracked, whereas saved searches are local runtime state.
DATA_DIR = Path(os.getenv("DEAL_AGENT_DATA_DIR", ".agent-state"))

store = SavedSearchStore(DATA_DIR / "saved_searches.json")
alert_service = AlertService(store=store, deals=deal_service)


def _poll_interval() -> float:
    try:
        return float(os.getenv("ALERT_POLL_SECONDS", "900"))
    except ValueError:
        return 900.0


async def _poll_saved_searches(interval: float) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            results = await asyncio.to_thread(alert_service.run_all)
        except Exception:  # noqa: BLE001 - the poller must survive any failure
            logger.exception("Saved-search poll failed")
            continue
        sent = sum(1 for result in results if result.alert is not None)
        if sent:
            logger.info("Saved-search poll sent %d alert email(s)", sent)


@asynccontextmanager
async def lifespan(app: FastAPI):
    interval = _poll_interval()
    task = None
    if interval > 0:
        task = asyncio.create_task(_poll_saved_searches(interval))
        logger.info("Polling saved searches every %.0fs", interval)
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="Arizona Deal Agent",
    description=(
        "Topic pages that live-update from allowlisted sources. "
        "Scam-signal titles are dropped."
    ),
    version=__version__,
    lifespan=lifespan,
)


def _budget_for(topic: str | None) -> float:
    spec = get_topic(topic)
    return spec.default_budget if spec else DEFAULT_BUDGET


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/topics", response_model=list[TopicInfo])
def list_topics() -> list[TopicInfo]:
    return topic_infos()


@app.get("/api/sources", response_model=list[SourceInfo])
def list_sources() -> list[SourceInfo]:
    return source_infos()


@app.get("/api/deals", response_model=DealsResponse)
def list_deals(
    query: str | None = Query(default=None, description="Search terms."),
    topic: str | None = Query(default=None, description="Topic page id or alias."),
    refresh: bool = Query(default=False, description="Bypass the scrape cache and pull live listings."),
) -> DealsResponse:
    """Source (or serve from cache) allowlisted listings for a topic."""
    if get_topic(topic) is None and topic:
        raise HTTPException(status_code=404, detail=f"Unknown topic: {topic}")
    search = query if topic is not None else (query or DEFAULT_QUERY)
    sourced = deal_service.get_deals(search, topic=topic, refresh=refresh)
    return DealsResponse(
        budget=_budget_for(topic),
        query=sourced.query,
        source=sourced.source,
        deals=sourced.deals,
        warning=sourced.warning,
        topic=sourced.topic,
        fetched_at=sourced.fetched_at,
    )


@app.post("/api/rank", response_model=RankResponse)
def rank(request: RankRequest) -> RankResponse:
    """Rank deals against a budget.

    Caller-supplied deals win; otherwise the cached scrape for ``query`` is
    used, which keeps repeated slider-driven calls off the network.
    """
    if request.topic and get_topic(request.topic) is None:
        raise HTTPException(status_code=404, detail=f"Unknown topic: {request.topic}")

    if request.deals:
        ranked = rank_deals(request.deals, request.budget, request.profit_weight)
        return ranked.model_copy(
            update={"source": "request", "query": request.query, "topic": request.topic}
        )

    sourced = deal_service.get_deals(request.query, topic=request.topic)
    ranked = rank_deals(sourced.deals, request.budget, request.profit_weight)
    return ranked.model_copy(
        update={
            "source": sourced.source,
            "query": sourced.query,
            "warning": sourced.warning,
            "topic": sourced.topic,
            "fetched_at": sourced.fetched_at,
        }
    )


@app.get("/api/saved-searches", response_model=list[SavedSearch])
def list_saved_searches() -> list[SavedSearch]:
    return store.list()


@app.post("/api/saved-searches", response_model=SavedSearchRunResult, status_code=201)
def create_saved_search(payload: SavedSearchCreate) -> SavedSearchRunResult:
    """Save a search and immediately check it, so matches alert right away."""
    search = store.add(payload)
    return alert_service.run(search)


@app.post("/api/saved-searches/{search_id}/run", response_model=SavedSearchRunResult)
def run_saved_search(search_id: str) -> SavedSearchRunResult:
    search = store.get(search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return alert_service.run(search)


@app.delete("/api/saved-searches/{search_id}", status_code=204, response_class=Response)
def delete_saved_search(search_id: str) -> Response:
    if not store.delete(search_id):
        raise HTTPException(status_code=404, detail="Saved search not found")
    return Response(status_code=204)


@app.get("/api/alerts", response_model=list[Alert])
def list_alerts(limit: int = Query(default=20, ge=1, le=200)) -> list[Alert]:
    """Most recent alert emails, newest first."""
    return store.alerts(limit)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/{topic_path}")
def topic_page(topic_path: str) -> FileResponse:
    if topic_path not in page_slugs():
        raise HTTPException(status_code=404, detail="Unknown topic page")
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
