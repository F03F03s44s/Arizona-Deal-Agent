"""Sourcing layer: scrape Craigslist once, then serve the result from cache.

The UI re-ranks on every slider tick, so ranking must not re-scrape. Deals are
cached per query and only refetched when the entry expires or is invalidated.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from . import craigslist
from .categories import DEFAULT_SEARCH_PATH, SEARCH_PATHS
from .craigslist import CraigslistError, Listing
from .data import DEFAULT_QUERY, SAMPLE_DEALS
from .market import listings_to_deals
from .craigslist import PHOENIX_AREA_ID as DEFAULT_AREA_ID
from .models import Deal

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 600.0

# Keep the whole page: every extra listing is another comparable, which is what
# the market-value estimate is built from.
DEFAULT_LIMIT = craigslist.PAGE_SIZE

Searcher = Callable[..., list[Listing]]


MAX_REMEMBERED = 5000

_CATEGORY_LABELS = {path: label for label, path in SEARCH_PATHS.items()}


@dataclass
class SourcedDeals:
    """Deals for a query plus where they actually came from."""

    deals: list[Deal]
    query: str
    source: str = "craigslist"
    warning: str | None = None
    category: str = DEFAULT_SEARCH_PATH
    seller_type: str | None = None
    area_id: int = DEFAULT_AREA_ID


@dataclass
class _CacheEntry:
    value: SourcedDeals
    expires_at: float


@dataclass
class DealService:
    """Fetches and caches deals for search queries."""

    searcher: Searcher = craigslist.search
    ttl: float = CACHE_TTL_SECONDS
    limit: int = DEFAULT_LIMIT
    _cache: dict[str, _CacheEntry] = field(default_factory=dict, repr=False)
    _by_id: dict[str, Deal] = field(default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def get_deals(
        self,
        query: str | None = None,
        *,
        category: str = DEFAULT_SEARCH_PATH,
        seller_type: str | None = None,
        area_id: int = DEFAULT_AREA_ID,
        refresh: bool = False,
    ) -> SourcedDeals:
        normalized = (query or "").strip()
        if not normalized and category == DEFAULT_SEARCH_PATH:
            normalized = DEFAULT_QUERY
        key = "|".join([normalized.lower(), category, seller_type or "any", str(area_id)])

        with self._lock:
            entry = self._cache.get(key)
            if entry and not refresh and entry.expires_at > time.monotonic():
                return entry.value

            sourced = self._fetch(normalized, category, seller_type, area_id)
            # Only cache successful scrapes, so a transient outage does not pin
            # the fallback data in place for the whole TTL.
            if sourced.source == "craigslist":
                self._cache[key] = _CacheEntry(sourced, time.monotonic() + self.ttl)
            self._remember(sourced.deals)
            return sourced

    def invalidate(self) -> None:
        with self._lock:
            self._cache.clear()
            self._by_id.clear()

    def remember(self, deals: list[Deal]) -> None:
        """Record deals so they can later be looked up by id."""
        with self._lock:
            self._remember(deals)

    def _remember(self, deals: list[Deal]) -> None:
        for deal in deals:
            self._by_id[deal.id] = deal
        if len(self._by_id) > MAX_REMEMBERED:
            excess = len(self._by_id) - MAX_REMEMBERED
            for key in list(self._by_id)[:excess]:
                del self._by_id[key]

    def find(self, deal_id: str) -> Deal | None:
        """Look up a deal the agent has already served.

        Detail and availability checks resolve ids through this rather than
        accepting a caller-supplied URL, so the server never fetches an
        arbitrary address on request.
        """
        with self._lock:
            return self._by_id.get(deal_id)

    def _fetch(
        self, query: str, category: str, seller_type: str | None, area_id: int
    ) -> SourcedDeals:
        described = query or _describe(category, seller_type)
        try:
            listings = self.searcher(
                query,
                category=category,
                seller_type=seller_type,
                area_id=area_id,
                limit=self.limit,
            )
        except CraigslistError as exc:
            logger.warning("Craigslist scrape failed for %r: %s", described, exc)
            return SourcedDeals(
                deals=list(SAMPLE_DEALS),
                query=query,
                source="sample",
                warning=f"Craigslist unavailable ({exc}); showing sample deals.",
                category=category,
                seller_type=seller_type,
                area_id=area_id,
            )

        deals = listings_to_deals(listings, category=described)
        if not deals:
            return SourcedDeals(
                deals=list(SAMPLE_DEALS),
                query=query,
                source="sample",
                warning=f"No priced Craigslist listings for {described!r}; showing sample deals.",
                category=category,
                seller_type=seller_type,
                area_id=area_id,
            )

        return SourcedDeals(
            deals=deals,
            query=query,
            source="craigslist",
            category=category,
            seller_type=seller_type,
            area_id=area_id,
        )


def _describe(category: str, seller_type: str | None) -> str:
    label = _CATEGORY_LABELS.get(category, category)
    return f"{label} ({seller_type})" if seller_type else label


deal_service = DealService()
