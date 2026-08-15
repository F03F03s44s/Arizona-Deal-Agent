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
    Deal(
        id="az-006",
        title="2018 Honda Civic (Glendale)",
        category="auto",
        acquisition_cost=9800,
        market_value=13200,
    ),
    Deal(
        id="az-007",
        title="Restaurant equipment pallet (Phoenix)",
        category="wholesale",
        acquisition_cost=2200,
        market_value=4100,
    ),
    Deal(
        id="az-008",
        title="Duplex down payment note (Avondale)",
        category="real-estate",
        acquisition_cost=28000,
        market_value=36000,
    ),
    Deal(
        id="az-009",
        title="iPhone / iPad refurb lot (Chandler)",
        category="electronics",
        acquisition_cost=3600,
        market_value=5200,
    ),
    Deal(
        id="az-010",
        title="Storage-unit auction pallet (Mesa)",
        category="general",
        acquisition_cost=400,
        market_value=1250,
    ),
    Deal(
        id="az-011",
        title="Ford F-150 work truck (Tucson)",
        category="auto",
        acquisition_cost=14500,
        market_value=18900,
    ),
    Deal(
        id="az-012",
        title="Hotel linen closeout (Scottsdale)",
        category="wholesale",
        acquisition_cost=900,
        market_value=2100,
    ),
    Deal(
        id="az-013",
        title="Condo assignment fee (Tempe)",
        category="real-estate",
        acquisition_cost=8500,
        market_value=12000,
    ),
    Deal(
        id="az-014",
        title="Gaming-PC parts lot (Phoenix)",
        category="electronics",
        acquisition_cost=2700,
        market_value=3900,
    ),
    Deal(
        id="az-015",
        title="Pawn-shop jewelry tray (Yuma)",
        category="general",
        acquisition_cost=1800,
        market_value=3400,
    ),
    Deal(
        id="az-016",
        title="Nissan Frontier (Flagstaff)",
        category="auto",
        acquisition_cost=11200,
        market_value=14100,
    ),
    Deal(
        id="az-017",
        title="Solar-panel pallet (Casa Grande)",
        category="wholesale",
        acquisition_cost=4800,
        market_value=7200,
    ),
    Deal(
        id="az-018",
        title="Land-contract trailer (Surprise)",
        category="real-estate",
        acquisition_cost=16500,
        market_value=21000,
    ),
    Deal(
        id="az-h01",
        title="3-bed ranch house (Phoenix)",
        category="house",
        acquisition_cost=215000,
        market_value=268000,
    ),
    Deal(
        id="az-h02",
        title="4-bed fixer house (Tucson)",
        category="house",
        acquisition_cost=189000,
        market_value=255000,
    ),
    Deal(
        id="az-h03",
        title="3-bed family house (Mesa)",
        category="house",
        acquisition_cost=249000,
        market_value=295000,
    ),
    Deal(
        id="az-h04",
        title="2-bed bungalow (Glendale)",
        category="house",
        acquisition_cost=175000,
        market_value=220000,
    ),
    Deal(
        id="az-h05",
        title="4-bed two-story house (Chandler)",
        category="house",
        acquisition_cost=320000,
        market_value=365000,
    ),
    Deal(
        id="az-h06",
        title="3-bed house near ASU (Tempe)",
        category="house",
        acquisition_cost=285000,
        market_value=330000,
    ),
    Deal(
        id="az-h07",
        title="5-bed house (Surprise)",
        category="house",
        acquisition_cost=298000,
        market_value=340000,
    ),
    Deal(
        id="az-h08",
        title="3-bed house (Yuma)",
        category="house",
        acquisition_cost=165000,
        market_value=210000,
    ),
    Deal(
        id="az-h09",
        title="4-bed house (Avondale)",
        category="house",
        acquisition_cost=240000,
        market_value=290000,
    ),
    Deal(
        id="az-h10",
        title="3-bed house (Casa Grande)",
        category="house",
        acquisition_cost=199000,
        market_value=245000,
    ),
    Deal(
        id="az-h11",
        title="4-bed house (Peoria)",
        category="house",
        acquisition_cost=310000,
        market_value=355000,
    ),
    Deal(
        id="az-h12",
        title="3-bed house (Goodyear)",
        category="house",
        acquisition_cost=255000,
        market_value=300000,
    ),
    Deal(
        id="az-h13",
        title="2-bed house (Sierra Vista)",
        category="house",
        acquisition_cost=149000,
        market_value=185000,
    ),
    Deal(
        id="az-h14",
        title="3-bed house (Buckeye)",
        category="house",
        acquisition_cost=229000,
        market_value=275000,
    ),
]

HOUSE_CATEGORIES = frozenset({"house", "real-estate"})
DEFAULT_BUDGET = 15000.0
DEFAULT_HOUSE_BUDGET = 350000.0


def deals_for_category(category: str | None) -> list[Deal]:
    """Return sample deals, optionally limited to houses / a category."""
    if not category:
        return list(SAMPLE_DEALS)
    wanted = category.strip().lower()
    if wanted in {"house", "houses", "property", "properties"}:
        return [deal for deal in SAMPLE_DEALS if deal.category.lower() in HOUSE_CATEGORIES]
    return [deal for deal in SAMPLE_DEALS if deal.category.lower() == wanted]
