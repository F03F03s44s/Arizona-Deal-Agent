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
from .craigslist import CraigslistError, Listing
from .data import DEFAULT_QUERY, SAMPLE_DEALS
from .market import listings_to_deals
from .models import Deal

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 600.0

# Keep the whole page: every extra listing is another comparable, which is what
# the market-value estimate is built from.
DEFAULT_LIMIT = craigslist.PAGE_SIZE

Searcher = Callable[..., list[Listing]]


@dataclass
class SourcedDeals:
    """Deals for a query plus where they actually came from."""

    deals: list[Deal]
    query: str
    source: str = "craigslist"
    warning: str | None = None


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
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def get_deals(self, query: str | None = None, *, refresh: bool = False) -> SourcedDeals:
        normalized = (query or DEFAULT_QUERY).strip() or DEFAULT_QUERY
        key = normalized.lower()

        with self._lock:
            entry = self._cache.get(key)
            if entry and not refresh and entry.expires_at > time.monotonic():
                return entry.value

            sourced = self._fetch(normalized)
            # Only cache successful scrapes, so a transient outage does not pin
            # the fallback data in place for the whole TTL.
            if sourced.source == "craigslist":
                self._cache[key] = _CacheEntry(sourced, time.monotonic() + self.ttl)
            return sourced

    def invalidate(self) -> None:
        with self._lock:
            self._cache.clear()

    def _fetch(self, query: str) -> SourcedDeals:
        try:
            listings = self.searcher(query, limit=self.limit)
        except CraigslistError as exc:
            logger.warning("Craigslist scrape failed for %r: %s", query, exc)
            return SourcedDeals(
                deals=list(SAMPLE_DEALS),
                query=query,
                source="sample",
                warning=f"Craigslist unavailable ({exc}); showing sample deals.",
            )

        deals = listings_to_deals(listings, category=query)
        if not deals:
            return SourcedDeals(
                deals=list(SAMPLE_DEALS),
                query=query,
                source="sample",
                warning=f"No priced Craigslist listings for {query!r}; showing sample deals.",
            )

        return SourcedDeals(deals=deals, query=query, source="craigslist")


deal_service = DealService()
