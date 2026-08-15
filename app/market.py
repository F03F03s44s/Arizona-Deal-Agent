"""Turn raw listings into scoreable deals by estimating market value.

A Craigslist post only tells you the asking price, but the ranking engine needs
a resale value too. The estimate here is the median asking price of comparable
listings in the same search: an item priced well under what similar items are
listed for is what the agent treats as profit.
"""

from __future__ import annotations

from statistics import median

from .craigslist import Listing
from .models import Deal

MIN_COMPARABLES = 3
STRONG_OVERLAP = 2

# Listings priced below this are almost always placeholders ($1 "call me"
# posts), which would otherwise look like infinite-margin deals.
MIN_CREDIBLE_PRICE = 20.0

STOPWORDS = frozenset(
    {
        "and",
        "for",
        "the",
        "with",
        "new",
        "used",
        "sale",
        "obo",
        "free",
        "good",
        "great",
        "nice",
        "excellent",
        "condition",
        "like",
        "very",
        "all",
        "one",
        "two",
        "set",
        "lot",
        "each",
        "some",
        "any",
        "you",
        "your",
        "our",
        "from",
        "this",
        "that",
        "have",
        "has",
        "will",
        "not",
        "are",
        "was",
        "can",
        "get",
        "off",
        "out",
        "big",
        "small",
        "must",
        "see",
        "call",
        "text",
        "only",
        "more",
        "less",
        "best",
        "price",
        "cash",
        "deal",
        "sell",
        "selling",
        "buy",
    }
)


def title_tokens(title: str) -> frozenset[str]:
    """Meaningful words in a listing title, used to find comparables."""
    cleaned = "".join(char.lower() if char.isalnum() else " " for char in title)
    return frozenset(
        word
        for word in cleaned.split()
        if len(word) >= 3 and word not in STOPWORDS and not word.isdigit()
    )


def _comparable_prices(
    index: int, listings: list[Listing], tokens: list[frozenset[str]]
) -> list[float]:
    """Prices of listings whose titles overlap ``listings[index]``.

    Tightly-matching titles are preferred, relaxing to a single shared word.
    Returns nothing when a listing has no real comparables: a search for power
    tools also drags in loafers and used cars, and pricing those off the rest
    of the cohort would invent margins that do not exist.
    """
    target = tokens[index]

    for threshold in (STRONG_OVERLAP, 1):
        prices = [
            listing.price
            for other, listing in enumerate(listings)
            if other != index and len(target & tokens[other]) >= threshold
        ]
        if len(prices) >= MIN_COMPARABLES:
            return prices

    return []


def listings_to_deals(
    listings: list[Listing],
    *,
    category: str = "general",
    source: str = "craigslist",
    source_label: str | None = None,
    id_prefix: str | None = None,
    min_price: float = MIN_CREDIBLE_PRICE,
) -> list[Deal]:
    """Convert listings into deals priced against their comparables."""
    usable = [listing for listing in listings if listing.price >= min_price]
    if len(usable) < 2:
        return []

    tokens = [title_tokens(listing.title) for listing in usable]

    deals: list[Deal] = []
    for index, listing in enumerate(usable):
        prices = _comparable_prices(index, usable, tokens)
        if not prices:
            continue
        market_value = float(median(prices))
        if market_value <= 0:
            continue

        prefix = id_prefix or ("cl" if source == "craigslist" else source[:8])
        label = source_label or (
            "Craigslist Phoenix (allowlisted)" if source == "craigslist" else source
        )
        deals.append(
            Deal(
                id=f"{prefix}-{listing.posting_id}",
                title=listing.title,
                category=category,
                acquisition_cost=listing.price,
                market_value=market_value,
                url=listing.url,
                location=listing.location,
                posted_at=listing.posted_at,
                source=source,
                source_label=label,
                comparable_count=len(prices),
            )
        )

    return deals
