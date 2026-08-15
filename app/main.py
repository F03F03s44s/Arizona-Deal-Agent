"""FastAPI application exposing the Arizona Deal Agent."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .agent import rank_deals
from .data import DEFAULT_BUDGET, SAMPLE_DEALS, deals_for_category
from .models import RankRequest, RankResponse

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Arizona Deal Agent",
    description="Ranks deals by profitability and affordability.",
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
    deals = request.deals or deals_for_category(request.category)
    return rank_deals(deals, request.budget, request.profit_weight)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
