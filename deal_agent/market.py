"""Arizona market baselines used to judge whether a listing is a deal.

Median sale price-per-sqft and typical monthly rent-per-sqft by city.
Figures are approximate metro-level baselines (compiled from public
Redfin/Zillow market pages) and are intentionally editable: tune them here
or override per-run once a live comps source is plugged in.
"""

from __future__ import annotations

from typing import NamedTuple


class CityMarket(NamedTuple):
    median_ppsf: float  # $ per sqft, recent sales
    rent_ppsf: float  # $ per sqft per month, long-term rental


# City name (title case) -> baseline stats.
AZ_MARKETS: dict[str, CityMarket] = {
    "Phoenix": CityMarket(282.0, 1.35),
    "Scottsdale": CityMarket(455.0, 1.65),
    "Tucson": CityMarket(215.0, 1.15),
    "Mesa": CityMarket(281.0, 1.30),
    "Chandler": CityMarket(305.0, 1.42),
    "Gilbert": CityMarket(298.0, 1.38),
    "Tempe": CityMarket(312.0, 1.50),
    "Glendale": CityMarket(258.0, 1.28),
    "Peoria": CityMarket(272.0, 1.25),
    "Surprise": CityMarket(243.0, 1.15),
    "Goodyear": CityMarket(258.0, 1.20),
    "Queen Creek": CityMarket(268.0, 1.18),
    "Buckeye": CityMarket(228.0, 1.10),
    "Casa Grande": CityMarket(198.0, 1.05),
    "Flagstaff": CityMarket(392.0, 1.55),
    "Prescott": CityMarket(332.0, 1.28),
    "Yuma": CityMarket(196.0, 1.00),
    "Sierra Vista": CityMarket(172.0, 0.95),
}

# Statewide fallback for cities we have no baseline for.
AZ_DEFAULT = CityMarket(265.0, 1.25)

# Bedroom count nudges rent-per-sqft: small units rent for more per sqft.
BEDS_RENT_MULTIPLIER: dict[int, float] = {0: 1.25, 1: 1.18, 2: 1.08, 3: 1.00, 4: 0.94, 5: 0.90}


def market_for(city: str) -> CityMarket:
    return AZ_MARKETS.get(city.strip().title(), AZ_DEFAULT)


def estimate_monthly_rent(city: str, sqft: float, beds: int | None) -> float:
    """Rough long-term rent estimate from city rent-per-sqft and size."""
    base = market_for(city).rent_ppsf * sqft
    if beds is not None:
        base *= BEDS_RENT_MULTIPLIER.get(max(0, min(beds, 5)), 0.90)
    return base
