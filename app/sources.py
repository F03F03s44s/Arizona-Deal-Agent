"""Where deals are scanned from.

A watch target is one (source, area, category, query, seller) combination. The
watcher sweeps a list of them, so widening coverage is a matter of adding
targets rather than changing code.

Only Craigslist ships as a source. Its robots.txt permits the search service
and posting pages this agent reads. The obvious next sources for homes do not:
Zillow answers 403, realtor.com rate-limits, and Redfin's robots.txt disallows
``/stingray/``. Adding one of those needs a licensed feed or an API key, which
is why :class:`DealSource` exists as an interface rather than being folded into
the Craigslist code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from . import craigslist
from .categories import DEFAULT_SEARCH_PATH, PROPERTY_SEARCH_PATHS, SEARCH_PATHS
from .craigslist import AREAS, PHOENIX_AREA_ID, SearchResult

DEFAULT_AREA_ID = PHOENIX_AREA_ID


@dataclass(frozen=True)
class WatchTarget:
    """One search the watcher sweeps on every pass."""

    area_id: int = DEFAULT_AREA_ID
    category: str = DEFAULT_SEARCH_PATH
    query: str = ""
    seller_type: str | None = None
    source: str = "craigslist"

    @property
    def key(self) -> str:
        return "|".join(
            [
                self.source,
                str(self.area_id),
                self.category,
                self.query.strip().lower(),
                self.seller_type or "any",
            ]
        )

    @property
    def is_property(self) -> bool:
        return self.category in PROPERTY_SEARCH_PATHS

    @property
    def label(self) -> str:
        area = AREAS.get(self.area_id, f"area {self.area_id}")
        category = _CATEGORY_LABELS.get(self.category, self.category)
        parts = [area, category]
        if self.query.strip():
            parts.append(f'"{self.query.strip()}"')
        if self.seller_type:
            parts.append(
                "dealers only" if self.seller_type == "dealer" else "owners only"
            )
        return " - ".join(parts)


_CATEGORY_LABELS = {path: label for label, path in SEARCH_PATHS.items()}


class DealSource(Protocol):
    """Fetches listings for a watch target."""

    name: str
    label: str

    def fetch(self, target: WatchTarget, *, limit: int) -> SearchResult: ...


class CraigslistSource:
    """Craigslist search, the one source that ships enabled."""

    name = "craigslist"
    label = "Craigslist"

    def fetch(
        self, target: WatchTarget, *, limit: int = craigslist.PAGE_SIZE
    ) -> SearchResult:
        return craigslist.search_page(
            target.query,
            area_id=target.area_id,
            category=target.category,
            seller_type=target.seller_type,
            limit=limit,
        )


SOURCES: dict[str, DealSource] = {CraigslistSource.name: CraigslistSource()}

# Scanned out of the box: everything for sale plus property, in Phoenix. Extra
# areas and categories are added through the API rather than being on by
# default, so a fresh install does not open with dozens of requests a minute.
DEFAULT_TARGETS: tuple[WatchTarget, ...] = (
    WatchTarget(area_id=DEFAULT_AREA_ID, category="sss"),
    WatchTarget(area_id=DEFAULT_AREA_ID, category="rea"),
)


def fetch(target: WatchTarget, *, limit: int = craigslist.PAGE_SIZE) -> SearchResult:
    """Fetch listings for one target through its source."""
    source = SOURCES.get(target.source)
    if source is None:
        raise craigslist.CraigslistError(f"Unknown source {target.source!r}")
    return source.fetch(target, limit=limit)
