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

# A comparable more than an order of magnitude away from the listing is not
# comparing like with like. Real estate searches are the clearest case: they
# return monthly rents alongside outright sale prices, and pricing a $2,600
# rental against a $378,000 sale invents a fortune in margin. A genuine flip
# is a small multiple, so this is wide enough to keep every real bargain.
MAX_COMP_RATIO = 10.0

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
    """Prices of listings comparable to ``listings[index]``.

    Tightly-matching titles are preferred, relaxing to a single shared word.
    Candidates outside :data:`MAX_COMP_RATIO` of the listing's own price are
    never used, and property listings only compare against others with the
    same bedroom count when enough of those exist.

    Returns nothing when a listing has no real comparables: a search for power
    tools also drags in loafers and used cars, and pricing those off the rest
    of the cohort would invent margins that do not exist.
    """
    target_tokens = tokens[index]
    target = listings[index]
    low = target.price / MAX_COMP_RATIO
    high = target.price * MAX_COMP_RATIO

    for same_bedrooms in (True, False):
        if same_bedrooms and target.bedrooms is None:
            continue
        for threshold in (STRONG_OVERLAP, 1):
            prices = [
                other.price
                for position, other in enumerate(listings)
                if position != index
                and low <= other.price <= high
                and len(target_tokens & tokens[position]) >= threshold
                and (not same_bedrooms or other.bedrooms == target.bedrooms)
            ]
            if len(prices) >= MIN_COMPARABLES:
                return prices

    return []


def _property_comps(index: int, listings: list[Listing]) -> tuple[float, int] | None:
    """Value a property from what comparable homes cost per square foot.

    A real-estate search returns land, rentals and sales side by side, and
    their prices are not the same kind of number. Square footage is the one
    thing that makes them comparable, so a property with no square footage is
    left unpriced rather than measured against whatever else came back.
    """
    target = listings[index]
    if not target.area_sqft or not target.bedrooms:
        return None

    rates = [
        other.price / other.area_sqft
        for position, other in enumerate(listings)
        if position != index
        and other.area_sqft
        and other.bedrooms == target.bedrooms
        and other.price / other.area_sqft <= (target.price / target.area_sqft) * MAX_COMP_RATIO
        and other.price / other.area_sqft >= (target.price / target.area_sqft) / MAX_COMP_RATIO
    ]
    if len(rates) < MIN_COMPARABLES:
        return None

    return float(median(rates)) * target.area_sqft, len(rates)


def listings_to_deals(
    listings: list[Listing],
    *,
    category: str = "general",
    source: str = "craigslist",
    min_price: float = MIN_CREDIBLE_PRICE,
) -> list[Deal]:
    """Convert listings into deals priced against their comparables."""
    usable = [listing for listing in listings if listing.price >= min_price]
    if len(usable) < 2:
        return []

    tokens = [title_tokens(listing.title) for listing in usable]

    deals: list[Deal] = []
    for index, listing in enumerate(usable):
        if listing.is_property:
            valued = _property_comps(index, usable)
            if valued is None:
                continue
            market_value, comparable_count = valued
        else:
            prices = _comparable_prices(index, usable, tokens)
            if not prices:
                continue
            market_value = float(median(prices))
            comparable_count = len(prices)

        if market_value <= 0:
            continue

        deals.append(
            Deal(
                id=f"cl-{listing.posting_id}",
                title=listing.title,
                category=listing.category_label or category,
                acquisition_cost=listing.price,
                market_value=market_value,
                url=listing.url,
                location=listing.location,
                posted_at=listing.posted_at,
                source=source,
                comparable_count=comparable_count,
                seller_type=listing.seller_type,
                bedrooms=listing.bedrooms,
                area_sqft=listing.area_sqft,
            )
        )

    return deals
