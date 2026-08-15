"""Deal inventory: live Craigslist scrape with offline sample fallback."""

from __future__ import annotations

import logging

from .models import Deal
from .scraper import scrape_phoenix_deals

logger = logging.getLogger(__name__)

# Kept only as an offline / scrape-failure fallback so ranking still works.
SAMPLE_DEALS: list[Deal] = [
    Deal(
        id="az-001",
        title="2015 Toyota Corolla (Phoenix)",
        category="auto",
        acquisition_cost=8200,
        market_value=11200,
        source="sample",
    ),
    Deal(
        id="az-002",
        title="Wholesale patio furniture lot (Tucson)",
        category="wholesale",
        acquisition_cost=1500,
        market_value=3200,
        source="sample",
    ),
    Deal(
        id="az-003",
        title="Fixer-upper mobile home (Mesa)",
        category="real-estate",
        acquisition_cost=42000,
        market_value=61000,
        source="sample",
    ),
    Deal(
        id="az-004",
        title="Refurbished MacBook lot (Scottsdale)",
        category="electronics",
        acquisition_cost=5400,
        market_value=6100,
        source="sample",
    ),
    Deal(
        id="az-005",
        title="Estate-sale tool collection (Tempe)",
        category="tools",
        acquisition_cost=650,
        market_value=1800,
        source="sample",
    ),
]

DEFAULT_BUDGET = 15000.0


def load_deals(
    *,
    query: str | None = None,
    refresh: bool = False,
    allow_sample_fallback: bool = True,
) -> tuple[list[Deal], str]:
    """Return live Phoenix Craigslist deals, or sample data if scrape fails."""
    try:
        deals = scrape_phoenix_deals(query=query, refresh=refresh)
        if deals:
            return deals, "craigslist"
        logger.warning("Craigslist scrape returned zero deals")
    except Exception:
        logger.exception("Craigslist scrape failed")

    if allow_sample_fallback:
        return list(SAMPLE_DEALS), "sample"
    return [], "empty"
