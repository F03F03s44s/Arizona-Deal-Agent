"""FastAPI application exposing the Arizona Deal Agent."""

from __future__ import annotations

from pathlib import Path

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .agent import rank_deals
from .data import DEFAULT_BUDGET, SAMPLE_DEALS
from .models import RankRequest, RankResponse, SendRequest, TransmissionRecord
from .transmit import STORE, TransmissionError, receive_inbox, transmit

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Arizona Deal Agent",
    description="Ranks deals by profitability and affordability, then sends the result.",
    version=__version__,
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/deals")
def list_deals() -> dict[str, object]:
    """Return the seeded sample deals and default budget."""
    return {"budget": DEFAULT_BUDGET, "deals": [d.model_dump() for d in SAMPLE_DEALS]}


@app.post("/api/rank", response_model=RankResponse)
def rank(request: RankRequest) -> RankResponse:
    """Rank a caller-provided set of deals against a budget."""
    deals = request.deals or SAMPLE_DEALS
    return rank_deals(deals, request.budget, request.profit_weight)


@app.post("/api/send", response_model=TransmissionRecord)
def send(request: SendRequest) -> TransmissionRecord:
    """Rank deals and transmit the recommendation to inbox, webhook, or log."""
    deals = request.deals or SAMPLE_DEALS
    ranking = rank_deals(deals, request.budget, request.profit_weight)
    try:
        return transmit(
            ranking,
            destination=request.destination,
            webhook_url=request.webhook_url,
            note=request.note,
            include_ranking=request.include_ranking,
            payload_format=request.payload_format,
        )
    except TransmissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/transmissions", response_model=list[TransmissionRecord])
def list_transmissions() -> list[TransmissionRecord]:
    """Return recent outbound sends (newest first)."""
    return STORE.list_outbox()


@app.get("/api/inbox", response_model=list[TransmissionRecord])
def list_inbox() -> list[TransmissionRecord]:
    """Return recent inbound deliveries (newest first)."""
    return STORE.list_inbox()


@app.post("/api/inbox", response_model=TransmissionRecord)
def post_inbox(payload: dict[str, Any]) -> TransmissionRecord:
    """Accept an inbound transmission payload from an external sender."""
    return receive_inbox(payload)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
