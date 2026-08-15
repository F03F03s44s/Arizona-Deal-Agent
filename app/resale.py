"""Conservative resale estimates for free-pile listings.

Free Craigslist posts have no asking price, so comparable-median math cannot
see a return. These keyword floors are deliberately low; they only exist so
a working TV ranks above a broken chair. They are not appraisals.
"""

from __future__ import annotations

from .craigslist import Listing
from .models import Deal

# Skip free posts that are unlikely to resell at a profit.
DEAD_PHRASES = (
    "parts only",
    "for parts",
    "not working",
    "doesn't work",
    "does not work",
    "non working",
    "as-is broken",
    "needs repair",
)

# First matching group wins. Values are conservative Phoenix resale floors.
RESALE_RULES: tuple[tuple[tuple[str, ...], float], ...] = (
    (("riding mower",), 350.0),
    (("lawn mower", "push mower", "mower"), 70.0),
    (("generator",), 120.0),
    (("pressure washer",), 60.0),
    (("iphone",), 100.0),
    (("ipad",), 70.0),
    (("macbook",), 200.0),
    (("laptop", "notebook"), 80.0),
    (("desktop", "imac"), 50.0),
    (("monitor",), 40.0),
    (("television", " tv ", "tv,", "flat screen"), 60.0),
    (("bike", "bicycle"), 50.0),
    (("scooter",), 40.0),
    (("washer", "dryer", "laundry"), 80.0),
    (("refrigerator", "fridge"), 90.0),
    (("dishwasher",), 40.0),
    (("sofa", "couch", "sectional"), 80.0),
    (("mattress",), 40.0),
    (("dresser", "nightstand"), 30.0),
    (("table saw", "miter saw", "circular saw"), 50.0),
    (("drill", "impact driver", "dewalt", "milwaukee", "makita"), 40.0),
    (("toolbox", "tool chest"), 40.0),
    (("air conditioner", "ac unit", "window ac"), 50.0),
    (("grill", "smoker"), 40.0),
    (("stroller",), 25.0),
    (("crib",), 30.0),
)

MIN_FREE_RETURN = 25.0
FREE_ACQUISITION = 1.0


def estimate_resale(title: str) -> float:
    """Return a conservative resale floor, or 0 if the post looks unsellable."""
    text = f" {title.lower()} "
    if any(phrase in text for phrase in DEAD_PHRASES):
        return 0.0
    for keywords, value in RESALE_RULES:
        if any(keyword in text for keyword in keywords):
            return value
    return 0.0


def free_listings_to_deals(listings: list[Listing], *, category: str = "free") -> list[Deal]:
    """Turn free posts into deals ranked by estimated resale, not asking price."""
    deals: list[Deal] = []
    for listing in listings:
        market = estimate_resale(listing.title)
        if market < MIN_FREE_RETURN:
            continue
        deals.append(
            Deal(
                id=f"cl-{listing.posting_id}",
                title=listing.title,
                category=category,
                acquisition_cost=FREE_ACQUISITION,
                market_value=market,
                url=listing.url,
                location=listing.location,
                posted_at=listing.posted_at,
                source="craigslist",
                source_label="Craigslist free (allowlisted)",
                verified=True,
                comparable_count=0,
            )
        )
    return deals
