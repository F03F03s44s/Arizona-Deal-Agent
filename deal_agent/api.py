"""FastAPI app: JSON API for ranked deals + serves the web UI.

Run:  uvicorn deal_agent.api:app --reload
Env:  DEAL_AGENT_CSV=/path/to/export.csv   to rank a real CSV export
      DEAL_AGENT_JSON=/path/to/data.json   to rank a custom JSON dataset
"""

from __future__ import annotations

import os
import statistics
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .models import Deal
from .scoring import rank_deals
from .sources import load_listings

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Arizona Deal Agent", version=__version__)


@lru_cache(maxsize=1)
def get_ranked_deals() -> tuple[Deal, ...]:
    listings = load_listings(
        csv_path=os.environ.get("DEAL_AGENT_CSV") or None,
        json_path=os.environ.get("DEAL_AGENT_JSON") or None,
    )
    return tuple(rank_deals(listings))


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/cities")
def cities() -> list[dict]:
    """Distinct cities in the loaded dataset with counts and median price."""
    by_city: dict[str, list[float]] = {}
    for deal in get_ranked_deals():
        by_city.setdefault(deal.listing.city, []).append(deal.listing.price)
    return [
        {"city": city, "count": len(prices), "median_price": round(statistics.median(prices))}
        for city, prices in sorted(by_city.items())
    ]


@app.get("/api/deals")
def deals(
    city: Optional[str] = None,
    max_price: Optional[float] = Query(default=None, gt=0),
    min_beds: Optional[int] = Query(default=None, ge=0),
    min_score: Optional[float] = Query(default=None, ge=0, le=100),
    property_type: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    results = list(get_ranked_deals())
    if city:
        results = [d for d in results if d.listing.city.lower() == city.strip().lower()]
    if max_price is not None:
        results = [d for d in results if d.listing.price <= max_price]
    if min_beds is not None:
        results = [d for d in results if (d.listing.beds or 0) >= min_beds]
    if min_score is not None:
        results = [d for d in results if d.deal_score >= min_score]
    if property_type:
        results = [d for d in results if d.listing.property_type == property_type]

    total = len(results)
    results = results[:limit]
    return {
        "total": total,
        "returned": len(results),
        "deals": [d.model_dump(by_alias=True) for d in results],
    }


@app.get("/api/deals/{listing_id}")
def deal_detail(listing_id: str) -> dict:
    for deal in get_ranked_deals():
        if deal.listing.id == listing_id:
            return deal.model_dump(by_alias=True)
    raise HTTPException(status_code=404, detail=f"No listing with id {listing_id}")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
