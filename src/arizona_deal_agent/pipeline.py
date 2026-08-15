"""The end-to-end search: find candidates, enrich them, underwrite, rank."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import sources as source_registry
from .enrich import enrich
from .market import MarketData, load_snapshot
from .models import Assumptions, Budget, Listing, ScoredDeal, Weights
from .scoring import rank, score_listing

DEFAULT_SOURCES = ("hud-reo", "sample")


@dataclass
class SearchRequest:
    """Everything that defines one search."""

    sources: list[str] = field(default_factory=lambda: list(DEFAULT_SOURCES))
    assumptions: Assumptions = field(default_factory=Assumptions)
    budget: Budget = field(default_factory=Budget)
    weights: Weights = field(default_factory=Weights)
    cities: list[str] = field(default_factory=list)
    zips: list[str] = field(default_factory=list)
    fetch_limit: int | None = None
    top: int | None = None
    include_over_budget: bool = False


@dataclass
class SearchResult:
    """Ranked deals plus enough context to trust and reproduce the ranking."""

    deals: list[ScoredDeal]
    request: SearchRequest
    source_reports: list[source_registry.SourceResult] = field(default_factory=list)
    found: int = 0
    scored: int = 0
    filtered_out: int = 0
    over_budget: int = 0
    market_as_of: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def best(self) -> ScoredDeal | None:
        return self.deals[0] if self.deals else None


def _address_key(listing: Listing) -> str:
    address = "".join(ch for ch in listing.address.lower() if ch.isalnum())
    return f"{address}|{listing.zip_code}" if address else f"id:{listing.id.lower()}"


def dedupe(listings: list[Listing]) -> list[Listing]:
    """Drop repeats, preferring the first entry that carries a price."""
    best: dict[str, Listing] = {}
    order: list[str] = []
    for listing in listings:
        key = _address_key(listing)
        existing = best.get(key)
        if existing is None:
            best[key] = listing
            order.append(key)
        elif existing.list_price is None and listing.list_price is not None:
            best[key] = listing
    return [best[key] for key in order]


def _matches(listing: Listing, cities: list[str], zips: list[str]) -> bool:
    if cities and listing.city.strip().lower() not in {c.strip().lower() for c in cities}:
        return False
    if zips and listing.zip_code not in {z.strip() for z in zips}:
        return False
    return True


def search(request: SearchRequest, market: MarketData | None = None) -> SearchResult:
    """Run a full search and return ranked deals."""
    data = market if market is not None else load_snapshot()
    reports = source_registry.collect(request.sources, limit=request.fetch_limit)

    listings: list[Listing] = []
    errors: list[str] = []
    for report in reports:
        listings.extend(report.listings)
        if report.error:
            errors.append(f"{report.name}: {report.error}")

    found = len(listings)
    listings = dedupe(listings)
    kept = [listing for listing in listings if _matches(listing, request.cities, request.zips)]
    filtered_out = len(listings) - len(kept)

    scored = [
        score_listing(
            listing,
            enrich(listing, data).inputs,
            request.assumptions,
            request.budget,
            request.weights,
        )
        for listing in kept
    ]

    over_budget = sum(1 for deal in scored if not deal.fits_budget)
    if not request.include_over_budget:
        scored = [deal for deal in scored if deal.fits_budget]

    ranked = rank(scored)
    if request.top:
        ranked = ranked[: request.top]

    return SearchResult(
        deals=ranked,
        request=request,
        source_reports=reports,
        found=found,
        scored=len(scored),
        filtered_out=filtered_out,
        over_budget=over_budget,
        market_as_of=data.value_as_of,
        errors=errors,
    )
