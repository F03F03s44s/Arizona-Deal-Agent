"""Sourcing layer: scrape allowlisted Craigslist once, then serve from cache.

The UI re-ranks on every slider tick, so ranking must not re-scrape. Deals are
cached per (topic, query) and only refetched when the entry expires or is
invalidated. Property pages always include the curated Arizona house catalog.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from . import craigslist
from .catalog import load_catalog_deals
from .craigslist import CraigslistError, Listing
from .data import DEFAULT_QUERY, SAMPLE_DEALS
from .market import listings_to_deals
from .models import Deal
from .topics import Topic, get_topic
from .trust import filter_live_deals

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
    topic: str | None = None


@dataclass
class _CacheEntry:
    value: SourcedDeals
    expires_at: float


def _cache_key(topic: str | None, query: str) -> str:
    return f"{topic or '-'}|{query.lower()}"


@dataclass
class DealService:
    """Fetches and caches deals for search queries."""

    searcher: Searcher = craigslist.search
    ttl: float = CACHE_TTL_SECONDS
    limit: int = DEFAULT_LIMIT
    _cache: dict[str, _CacheEntry] = field(default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def get_deals(
        self,
        query: str | None = None,
        *,
        topic: str | None = None,
        refresh: bool = False,
    ) -> SourcedDeals:
        spec = get_topic(topic)
        if spec is None:
            normalized = (query or DEFAULT_QUERY).strip() or DEFAULT_QUERY
        else:
            normalized = (query or spec.default_query).strip() or spec.default_query
        key = _cache_key(spec.id if spec else None, normalized)

        with self._lock:
            entry = self._cache.get(key)
            if entry and not refresh and entry.expires_at > time.monotonic():
                return entry.value

            sourced = self._fetch(normalized, spec)
            # Only cache successful live scrapes, so a transient outage does
            # not pin the fallback data in place for the whole TTL.
            if "craigslist" in sourced.source or sourced.source == "verified-catalog":
                self._cache[key] = _CacheEntry(sourced, time.monotonic() + self.ttl)
            return sourced

    def invalidate(self) -> None:
        with self._lock:
            self._cache.clear()

    def _scrape(self, query: str, spec: Topic | None) -> tuple[list[Deal], str | None]:
        search_path = spec.craigslist_path if spec else "sss"
        min_price = spec.min_live_price if spec else 20.0
        try:
            listings = self.searcher(query, limit=self.limit, search_path=search_path)
        except CraigslistError as exc:
            logger.warning("Craigslist scrape failed for %r: %s", query, exc)
            return [], f"Craigslist unavailable ({exc})"

        deals = listings_to_deals(listings, category=query, min_price=min_price)
        deals = filter_live_deals(deals)
        if not deals:
            return [], f"No priced Craigslist listings for {query!r}"
        return deals, None

    def _fetch(self, query: str, spec: Topic | None) -> SourcedDeals:
        topic_id = spec.id if spec else None

        if spec is not None and spec.uses_catalog:
            catalog = load_catalog_deals(query)
            live, live_warning = self._scrape(query, spec)
            deals = list(catalog)
            deals.extend(live)
            parts = ["verified-catalog"]
            if live:
                parts.append("craigslist")
            warning = None
            if live_warning and not live:
                warning = f"{live_warning}; showing the verified Arizona house catalog."
            return SourcedDeals(
                deals=deals,
                query=query,
                source="+".join(parts),
                warning=warning,
                topic=topic_id,
            )

        live, live_warning = self._scrape(query, spec)
        if live:
            return SourcedDeals(
                deals=live,
                query=query,
                source="craigslist",
                topic=topic_id,
            )

        fallback_warning = (
            f"{live_warning}; showing sample deals."
            if live_warning
            else "No allowlisted listings; showing sample deals."
        )
        if live_warning and "unavailable" in live_warning:
            fallback_warning = f"{live_warning}; showing sample deals."
        elif live_warning and "No priced" in live_warning:
            fallback_warning = f"{live_warning}; showing sample deals."

        return SourcedDeals(
            deals=list(SAMPLE_DEALS),
            query=query,
            source="sample",
            warning=fallback_warning,
            topic=topic_id,
        )


deal_service = DealService()
