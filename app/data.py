"""Sample Arizona deals used to seed the demo."""

from __future__ import annotations

from .models import Deal

SAMPLE_DEALS: list[Deal] = [
    Deal(
        id="az-001",
        title="2015 Toyota Corolla (Phoenix)",
        category="auto",
        acquisition_cost=8200,
        market_value=11200,
    ),
    Deal(
        id="az-002",
        title="Wholesale patio furniture lot (Tucson)",
        category="wholesale",
        acquisition_cost=1500,
        market_value=3200,
    ),
    Deal(
        id="az-003",
        title="Fixer-upper mobile home (Mesa)",
        category="real-estate",
        acquisition_cost=42000,
        market_value=61000,
    ),
    Deal(
        id="az-004",
        title="Refurbished MacBook lot (Scottsdale)",
        category="electronics",
        acquisition_cost=5400,
        market_value=6100,
    ),
    Deal(
        id="az-005",
        title="Estate-sale tool collection (Tempe)",
        category="general",
        acquisition_cost=650,
        market_value=1800,
    ),
]

DEFAULT_BUDGET = 15000.0
