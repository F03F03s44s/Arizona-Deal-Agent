"""FastAPI application exposing the Arizona Deal Agent."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, craigslist, sources
from .agent import rank_deals
from .alerts import AlertService, SavedSearchStore
from .categories import DEALER, DEFAULT_SEARCH_PATH, OWNER, PROPERTY_SEARCH_PATHS, SEARCH_PATHS
from .craigslist import ListingStatus
from .data import DEFAULT_BUDGET, DEFAULT_QUERY
from .deals import deal_service
from .models import (
    Alert,
    AvailabilityResult,
    DealsResponse,
    Finding,
    ListingDetailModel,
    MetaResponse,
    RankRequest,
    RankResponse,
    SavedSearch,
    SavedSearchCreate,
    SavedSearchRunResult,
    SourceInfo,
    WatchConfigModel,
    WatchStatus,
    WatchTargetModel,
)
from .sources import AREAS, DEFAULT_AREA_ID, WatchTarget
from .watcher import DealWatcher, WatchConfig, run_watch_loop

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Make this package's logs visible.

    Uvicorn only configures its own loggers, so without this a background scan
    runs completely silently and there is no way to tell it is alive.
    """
    package_logger = logging.getLogger("app")
    package_logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    if not package_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s - %(message)s"))
        package_logger.addHandler(handler)


_configure_logging()

STATIC_DIR = Path(__file__).parent / "static"
# Not "data/": that directory holds the CLI's sample listings, which are
# tracked, whereas saved searches are local runtime state.
DATA_DIR = Path(os.getenv("DEAL_AGENT_DATA_DIR", ".agent-state"))

CONTACT_NOTE = (
    "Craigslist keeps seller contact details behind its reply flow, which its "
    "robots.txt disallows scraping. Use the listing's reply button; any phone "
    "or email below is one the seller published in the posting text itself."
)

store = SavedSearchStore(DATA_DIR / "saved_searches.json")
alert_service = AlertService(store=store, deals=deal_service)
watcher = DealWatcher()


def _poll_interval() -> float:
    try:
        return float(os.getenv("ALERT_POLL_SECONDS", "900"))
    except ValueError:
        return 900.0


def _watch_enabled() -> bool:
    return os.getenv("WATCH_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}


def _notify_findings(findings: list) -> None:
    """Email newly-found deals, if the watcher has somewhere to send them."""
    email = getattr(watcher.config, "email", None)
    if not email or not findings:
        return
    alert_service.notify_findings(
        findings, email=email, min_score=watcher.config.min_score
    )


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
    tasks: list[asyncio.Task] = []

    interval = _poll_interval()
    if interval > 0:
        tasks.append(asyncio.create_task(_poll_saved_searches(interval)))
        logger.info("Polling saved searches every %.0fs", interval)

    if _watch_enabled():
        watcher.config.enabled = True
        tasks.append(asyncio.create_task(run_watch_loop(watcher, _notify_findings)))
        logger.info(
            "Watching %d target(s) every %.0fs",
            len(watcher.config.targets),
            watcher.config.interval,
        )
    else:
        watcher.config.enabled = False

    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="Arizona Deal Agent",
    description="Scrapes Phoenix Craigslist and ranks listings by profitability and affordability.",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    """Filter options and the state of every scan source."""
    return MetaResponse(
        areas=AREAS,
        categories=SEARCH_PATHS,
        property_categories=sorted(PROPERTY_SEARCH_PATHS),
        seller_types={OWNER: "Private sellers", DEALER: "Dealers & wholesalers"},
        sources=[
            SourceInfo(name="craigslist", label="Craigslist", enabled=True),
            SourceInfo(
                name="zillow",
                label="Zillow",
                enabled=False,
                note="Answers 403 to automated requests; needs a licensed feed.",
            ),
            SourceInfo(
                name="redfin",
                label="Redfin",
                enabled=False,
                note="robots.txt disallows /stingray/, which is where its search API lives.",
            ),
            SourceInfo(
                name="realtor",
                label="Realtor.com",
                enabled=False,
                note="Rate-limits automated requests (HTTP 429).",
            ),
        ],
    )


@app.get("/api/deals", response_model=DealsResponse)
def list_deals(
    query: str = Query(default=DEFAULT_QUERY, description="Search terms."),
    category: str = Query(default=DEFAULT_SEARCH_PATH, description="Craigslist search path."),
    seller_type: str | None = Query(default=None, description="owner or dealer."),
    area_id: int = Query(default=DEFAULT_AREA_ID, description="Craigslist area id."),
    refresh: bool = Query(default=False, description="Bypass the scrape cache."),
) -> DealsResponse:
    """Scrape (or serve from cache) listings for a search."""
    sourced = deal_service.get_deals(
        query,
        category=category,
        seller_type=seller_type,
        area_id=area_id,
        refresh=refresh,
    )
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

    Caller-supplied deals win; otherwise the cached scrape for the requested
    search is used, which keeps repeated slider-driven calls off the network.
    """
    if request.deals:
        ranked = rank_deals(request.deals, request.budget, request.profit_weight)
        return ranked.model_copy(update={"source": "request", "query": request.query})

    sourced = deal_service.get_deals(
        request.query,
        category=request.category,
        seller_type=request.seller_type,
        area_id=request.area_id,
    )
    ranked = rank_deals(sourced.deals, request.budget, request.profit_weight)
    return ranked.model_copy(
        update={
            "source": sourced.source,
            "query": sourced.query,
            "warning": sourced.warning,
        }
    )


def _require_deal(deal_id: str):
    deal = deal_service.find(deal_id)
    if deal is None or not deal.url:
        raise HTTPException(status_code=404, detail="Unknown deal, or it has no listing page")
    return deal


@app.get("/api/deals/{deal_id}/detail", response_model=ListingDetailModel)
def listing_detail(deal_id: str) -> ListingDetailModel:
    """Full posting: description, photos, attributes, where it is, how to reply."""
    deal = _require_deal(deal_id)
    try:
        detail = craigslist.fetch_detail(deal.url)
    except craigslist.CraigslistError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ListingDetailModel(
        posting_id=detail.posting_id,
        url=detail.url,
        title=detail.title or deal.title,
        status=detail.status.value,
        price=detail.price,
        description=detail.description,
        images=detail.images,
        attributes=detail.attributes,
        address=detail.address or deal.location,
        latitude=detail.latitude,
        longitude=detail.longitude,
        map_url=detail.map_url,
        posted_at=detail.posted_at,
        updated_at=detail.updated_at,
        category_label=detail.category_label,
        seller_type=detail.seller_type,
        phones=detail.phones,
        emails=detail.emails,
        reply_url=detail.reply_url,
        other_listings_url=detail.other_listings_url,
        contact_note=CONTACT_NOTE,
    )


@app.get("/api/deals/{deal_id}/availability", response_model=AvailabilityResult)
def listing_availability(deal_id: str) -> AvailabilityResult:
    """Check whether the listing is still up."""
    deal = _require_deal(deal_id)
    status = craigslist.check_status(deal.url)
    return AvailabilityResult(
        deal_id=deal_id,
        url=deal.url,
        status=status.value,
        still_available=status is ListingStatus.ACTIVE,
        checked_at=datetime.now(UTC),
    )


def _target_model(target: WatchTarget) -> WatchTargetModel:
    return WatchTargetModel(
        area_id=target.area_id,
        category=target.category,
        query=target.query,
        seller_type=target.seller_type,
        source=target.source,
        key=target.key,
        label=target.label,
        is_property=target.is_property,
    )


def _watch_status() -> WatchStatus:
    return WatchStatus(
        enabled=watcher.config.enabled,
        interval=watcher.config.interval,
        min_score=watcher.config.min_score,
        email=getattr(watcher.config, "email", None),
        targets=[_target_model(t) for t in watcher.config.targets],
        last_swept_at=watcher.last_swept_at,
        source_refreshed_at=watcher.source_refreshed_at,
        last_error=watcher.last_error,
        findings_held=len(watcher.recent(limit=1000)),
    )


@app.get("/api/watch", response_model=WatchStatus)
def watch_status() -> WatchStatus:
    return _watch_status()


@app.put("/api/watch", response_model=WatchStatus)
def update_watch(config: WatchConfigModel) -> WatchStatus:
    """Change what is scanned, how often, and where alerts go."""
    targets = [
        WatchTarget(
            area_id=t.area_id,
            category=t.category,
            query=t.query,
            seller_type=t.seller_type,
            source=t.source,
        )
        for t in config.targets
    ] or list(sources.DEFAULT_TARGETS)

    watcher.config = WatchConfig(
        targets=targets,
        interval=config.interval,
        min_score=config.min_score,
        budget=config.budget,
        profit_weight=config.profit_weight,
        enabled=config.enabled,
        email=config.email,
    )
    return _watch_status()


@app.post("/api/watch/sweep", response_model=list[Finding])
def sweep_now() -> list[Finding]:
    """Run one sweep immediately instead of waiting for the interval."""
    findings = watcher.sweep()
    _notify_findings(findings)
    return [finding.to_model() for finding in findings]


@app.get("/api/watch/findings", response_model=list[Finding])
def watch_findings(limit: int = Query(default=50, ge=1, le=200)) -> list[Finding]:
    """Newly-posted deals the watcher has reported, newest first."""
    return [finding.to_model() for finding in watcher.recent(limit)]


@app.get("/api/watch/stream")
async def watch_stream() -> StreamingResponse:
    """Server-sent events, so the browser hears about a find as it happens."""
    queue = watcher.subscribe()

    async def events():
        try:
            yield "retry: 3000\n\n"
            while True:
                try:
                    finding = await asyncio.wait_for(queue.get(), timeout=20)
                except TimeoutError:
                    # Keeps proxies from closing an idle stream.
                    yield ": keep-alive\n\n"
                    continue
                yield f"data: {json.dumps(finding.as_dict())}\n\n"
        finally:
            watcher.unsubscribe(queue)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
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


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
