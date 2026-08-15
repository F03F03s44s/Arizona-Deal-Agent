"""HTTP API and web UI.

The API returns exactly what the CLI's ``--format json`` returns, so the two
surfaces can never drift in how they describe a deal.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import __version__
from ..market import load_snapshot
from ..models import Assumptions, Budget, Weights, as_rate
from ..pipeline import SearchRequest, search
from ..report import result_to_dict
from ..sources import available_sources

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Arizona Deal Agent",
    version=__version__,
    description="Find Arizona property deals and rank them by best value.",
)


class SearchBody(BaseModel):
    """Search parameters accepted by ``POST /api/search``."""

    sources: list[str] = Field(default_factory=lambda: ["hud-reo", "sample"])
    cities: list[str] = Field(default_factory=list)
    zips: list[str] = Field(default_factory=list)
    top: int | None = Field(default=50, ge=1, le=500)
    include_over_budget: bool = True

    max_price: float | None = Field(default=None, gt=0)
    budget_cash: float | None = Field(default=None, gt=0)
    budget_monthly: float | None = Field(default=None, gt=0)
    min_cash_flow: float | None = None
    min_cap_rate: float | None = None

    down_payment: float = Field(default=0.20, ge=0, le=100)
    rate: float = Field(default=0.065, ge=0, le=100)
    term: int = Field(default=30, ge=1, le=50)

    weight_discount: float = Field(default=0.25, ge=0, le=1)
    weight_profit: float = Field(default=0.40, ge=0, le=1)
    weight_afford: float = Field(default=0.35, ge=0, le=1)

    def to_request(self) -> SearchRequest:
        # Only built-in sources are reachable over HTTP. Accepting a path here
        # would let any caller read arbitrary CSV or JSON off the server.
        allowed = set(available_sources())
        unknown = [name for name in self.sources if name not in allowed]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"unknown source(s): {', '.join(unknown)}. Allowed: {', '.join(sorted(allowed))}",
            )
        if not self.sources:
            raise HTTPException(status_code=400, detail="pick at least one source")

        return SearchRequest(
            sources=list(self.sources),
            assumptions=Assumptions(
                down_payment_pct=self.down_payment,
                interest_rate=self.rate,
                term_years=self.term,
            ),
            budget=Budget(
                max_price=self.max_price,
                max_cash_to_close=self.budget_cash,
                max_monthly_payment=self.budget_monthly,
                min_cash_flow=self.min_cash_flow,
                min_cap_rate=as_rate(self.min_cap_rate) if self.min_cap_rate is not None else None,
            ),
            weights=Weights(
                discount=self.weight_discount,
                profitability=self.weight_profit,
                affordability=self.weight_afford,
            ),
            cities=list(self.cities),
            zips=list(self.zips),
            top=self.top,
            include_over_budget=self.include_over_budget,
        )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/sources")
def sources() -> dict:
    return {"sources": [{"name": n, "description": d} for n, d in available_sources().items()]}


@app.get("/api/market")
def market() -> dict:
    """Coverage and vintage of the packaged Arizona market snapshot."""
    data = load_snapshot()
    return {
        "generated_at": data.generated_at,
        "value_as_of": data.value_as_of,
        "rent_as_of": data.rent_as_of,
        "zip_count": len(data.zips),
        "city_count": len(data.cities),
        "median_value": round(data.median_value, 2),
        "median_rent": round(data.median_rent, 2),
    }


@app.post("/api/search")
def run_search(body: SearchBody) -> dict:
    return result_to_dict(search(body.to_request()))


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
