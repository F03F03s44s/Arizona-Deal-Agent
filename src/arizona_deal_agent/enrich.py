"""Fill in whatever a discovery source left blank, and say where it came from.

A HUD foreclosure feed publishes an address and nothing else; an agent's CSV
export usually has a price but no rent. Underwriting needs a price, a rent and
a market value for every candidate, so each gap is filled from the Arizona
market snapshot and tagged with its origin. Every downstream report shows those
tags, which keeps an estimate from being mistaken for a listed number.
"""

from __future__ import annotations

from dataclasses import dataclass

from .market import MarketData, ZipMarket
from .models import AZ_INSURANCE_RATE, AZ_TAX_RATE, DealInputs, Listing

LISTED = "listed"
ZHVI = "estimated:zhvi"
ZORI = "estimated:zori"
STATE_MEDIAN = "estimated:az-median"
STATE_YIELD = "estimated:az-yield"
AZ_AVERAGE = "estimated:az-average"
ASSUMED_NONE = "assumed:none"

PROVENANCE_LABELS = {
    LISTED: "from the listing",
    ZHVI: "Zillow ZHVI for this ZIP",
    ZORI: "Zillow ZORI for this ZIP",
    STATE_MEDIAN: "Arizona median home value",
    STATE_YIELD: "Arizona median rent-to-value",
    AZ_AVERAGE: "Arizona average tax and insurance rates",
    ASSUMED_NONE: "assumed none",
}


@dataclass(frozen=True)
class Enrichment:
    """The underwriting inputs plus the market context used to build them."""

    inputs: DealInputs
    market: ZipMarket | None
    scope: str


def describe(tag: str) -> str:
    """Human-readable version of a provenance tag."""
    return PROVENANCE_LABELS.get(tag, tag)


def _scope_for(listing: Listing, market: ZipMarket | None, data: MarketData) -> str:
    if market is None:
        return "Arizona statewide"
    if market.zip_code and market.zip_code == _zip(listing.zip_code):
        return f"ZIP {market.zip_code}"
    if market.city and not market.zip_code:
        return f"{market.city} city median"
    return f"ZIP {market.zip_code}" if market.zip_code else "Arizona statewide"


def _zip(value: str) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[:5].zfill(5) if digits else ""


def enrich(listing: Listing, data: MarketData) -> Enrichment:
    """Resolve a raw listing into a complete, underwritable set of inputs."""
    market = data.lookup(listing.zip_code, listing.city)
    scope = _scope_for(listing, market, data)
    provenance: dict[str, str] = {}

    typical_value = market.typical_value if market else None
    typical_rent = market.typical_rent if market else None

    if listing.market_value and listing.market_value > 0:
        market_value = float(listing.market_value)
        provenance["market_value"] = LISTED
    elif typical_value:
        market_value = float(typical_value)
        provenance["market_value"] = ZHVI
    else:
        market_value = data.median_value
        provenance["market_value"] = STATE_MEDIAN

    if listing.list_price and listing.list_price > 0:
        price = float(listing.list_price)
        provenance["price"] = LISTED
    else:
        # No published ask. The typical value of the surrounding ZIP is the
        # least speculative stand-in, and flagging it keeps the ranking honest.
        price = market_value
        provenance["price"] = provenance["market_value"].replace(LISTED, ZHVI)

    if listing.monthly_rent and listing.monthly_rent > 0:
        rent = float(listing.monthly_rent)
        provenance["rent"] = LISTED
    elif typical_rent:
        rent = float(typical_rent)
        provenance["rent"] = ZORI
    else:
        statewide_yield = (data.median_rent * 12.0) / data.median_value
        rent = market_value * statewide_yield / 12.0
        provenance["rent"] = STATE_YIELD

    if listing.annual_taxes is not None or listing.annual_insurance is not None:
        annual_taxes = float(listing.annual_taxes or 0.0)
        annual_insurance = float(listing.annual_insurance or 0.0)
        provenance["carrying_costs"] = LISTED
    else:
        annual_taxes = price * AZ_TAX_RATE
        annual_insurance = price * AZ_INSURANCE_RATE
        provenance["carrying_costs"] = AZ_AVERAGE

    provenance["hoa"] = LISTED if listing.monthly_hoa else ASSUMED_NONE
    provenance["market_scope"] = scope

    inputs = DealInputs(
        price=price,
        monthly_rent=rent,
        market_value=market_value,
        rehab_cost=float(listing.rehab_cost or 0.0),
        annual_taxes=annual_taxes,
        annual_insurance=annual_insurance,
        monthly_hoa=float(listing.monthly_hoa or 0.0),
        provenance=provenance,
    )
    return Enrichment(inputs=inputs, market=market, scope=scope)
