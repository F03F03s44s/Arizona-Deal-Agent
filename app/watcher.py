"""Continuous scan for newly-posted deals.

The watcher sweeps every configured target on a short interval, remembers the
posting ids it has already seen, and reports only what is genuinely new. The
first sweep of a target is deliberately silent: it records the existing backlog
rather than announcing several hundred listings that were already there.

Findings are published to in-process subscribers straight away, which is what
the browser's event stream and the email notifier both consume.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from . import sources
from .agent import score_deal
from .craigslist import CraigslistError, Listing
from .deals import deal_service
from .market import listings_to_deals
from .models import Finding as FindingModel
from .models import ScoredDeal
from .sources import WatchTarget

logger = logging.getLogger(__name__)

# Craigslist answers this search from a cache that only rolls every ~15
# minutes; polling faster returns byte-identical data. Sweeping every five
# minutes still catches a roll promptly without hammering them for nothing.
DEFAULT_INTERVAL = 300.0
SOURCE_CACHE_SECONDS = 900
DEFAULT_MIN_SCORE = 0.9
DEFAULT_BUDGET = 1_000_000.0
DEFAULT_PROFIT_WEIGHT = 0.6

# Anything posted within this window is called out as brand new.
FRESH_SECONDS = 900

MAX_EVENTS = 100
MAX_SEEN_PER_TARGET = 5000

# Craigslist is one site; sweeping many targets back to back without a pause
# would be rude regardless of how fast the loop could go.
PAUSE_BETWEEN_TARGETS = 1.0


@dataclass(frozen=True)
class Finding:
    """A newly-posted listing the watcher decided is worth reporting."""

    scored: ScoredDeal
    target_key: str
    target_label: str
    is_property: bool
    found_at: datetime
    age_seconds: float | None

    @property
    def is_fresh(self) -> bool:
        return self.age_seconds is not None and 0 <= self.age_seconds <= FRESH_SECONDS

    def to_model(self) -> FindingModel:
        return FindingModel(
            deal=self.scored,
            target_key=self.target_key,
            target_label=self.target_label,
            is_property=self.is_property,
            found_at=self.found_at,
            age_seconds=self.age_seconds,
            is_fresh=self.is_fresh,
        )

    def as_dict(self) -> dict:
        return self.to_model().model_dump(mode="json")


@dataclass
class WatchConfig:
    """What the watcher scans and what it considers worth reporting."""

    targets: list[WatchTarget] = field(default_factory=lambda: list(sources.DEFAULT_TARGETS))
    interval: float = DEFAULT_INTERVAL
    min_score: float = DEFAULT_MIN_SCORE
    budget: float = DEFAULT_BUDGET
    profit_weight: float = DEFAULT_PROFIT_WEIGHT
    enabled: bool = True
    email: str | None = None


class DealWatcher:
    """Sweeps watch targets and publishes newly-posted deals."""

    def __init__(
        self,
        config: WatchConfig | None = None,
        *,
        fetcher=sources.fetch,
        clock=lambda: datetime.now(UTC),
    ):
        self.config = config or WatchConfig()
        self._fetch = fetcher
        self._clock = clock
        self._seen: dict[str, set[str]] = {}
        self._cache_ts: dict[str, int] = {}
        self._events: deque[Finding] = deque(maxlen=MAX_EVENTS)
        self._subscribers: list[asyncio.Queue] = []
        self._lock = threading.Lock()
        self.last_swept_at: datetime | None = None
        self.source_refreshed_at: datetime | None = None
        self.last_error: str | None = None

    def reset(self, config: WatchConfig | None = None) -> None:
        """Forget every seen listing and finding, and optionally reconfigure."""
        with self._lock:
            self._seen.clear()
            self._cache_ts.clear()
            self._events.clear()
        self.config = config or WatchConfig()
        self.last_swept_at = None
        self.source_refreshed_at = None
        self.last_error = None

    # -- subscriptions ----------------------------------------------------

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=64)
        with self._lock:
            self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    def _publish(self, findings: Iterable[Finding]) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for finding in findings:
            for queue in subscribers:
                try:
                    queue.put_nowait(finding)
                except asyncio.QueueFull:
                    # A browser tab that cannot keep up is not a reason to
                    # hold up the sweep.
                    logger.debug("Dropping finding for a slow subscriber")

    # -- scanning ---------------------------------------------------------

    def recent(self, limit: int = 50) -> list[Finding]:
        with self._lock:
            return list(reversed(list(self._events)))[:limit]

    def sweep_target(self, target: WatchTarget) -> list[Finding]:
        """Scan one target and return the new listings worth reporting."""
        result = self._fetch(target)
        listings = result.listings

        if result.cache_ts is not None:
            self.source_refreshed_at = datetime.fromtimestamp(result.cache_ts, tz=UTC)
            if self._cache_ts.get(target.key) == result.cache_ts:
                # The source has not refreshed, so this is the same snapshot
                # already processed. Nothing can be new.
                return []
            self._cache_ts[target.key] = result.cache_ts

        first_pass = target.key not in self._seen
        seen = self._seen.setdefault(target.key, set())

        fresh_listings = [item for item in listings if item.posting_id not in seen]
        for item in listings:
            seen.add(item.posting_id)
        if len(seen) > MAX_SEEN_PER_TARGET:
            self._seen[target.key] = set(list(seen)[-MAX_SEEN_PER_TARGET:])

        if first_pass:
            logger.info(
                "Primed %s with %d existing listings", target.label, len(listings)
            )
            return []

        return self._report(target, listings, fresh_listings)

    def _report(
        self, target: WatchTarget, cohort: list[Listing], new_listings: list[Listing]
    ) -> list[Finding]:
        if not new_listings:
            return []

        # New listings are priced against the whole cohort, not just each
        # other, so a single new arrival still gets real comparables.
        priced = listings_to_deals(cohort, category=target.label)
        deals = {deal.id: deal for deal in priced}
        deal_service.remember(priced)
        now = self._clock()

        findings: list[Finding] = []
        for listing in new_listings:
            deal = deals.get(f"cl-{listing.posting_id}")
            if deal is None:
                continue
            scored = score_deal(deal, self.config.budget, self.config.profit_weight)
            if not scored.within_budget or scored.score < self.config.min_score:
                continue
            age = (now - listing.posted_at).total_seconds() if listing.posted_at else None
            findings.append(
                Finding(
                    scored=scored,
                    target_key=target.key,
                    target_label=target.label,
                    is_property=target.is_property,
                    found_at=now,
                    age_seconds=age,
                )
            )

        findings.sort(key=lambda f: f.scored.score, reverse=True)
        return findings

    def sweep(self) -> list[Finding]:
        """Scan every configured target once."""
        found: list[Finding] = []
        errors: list[str] = []

        for index, target in enumerate(self.config.targets):
            if index:
                time.sleep(PAUSE_BETWEEN_TARGETS)
            try:
                found.extend(self.sweep_target(target))
            except CraigslistError as exc:
                logger.warning("Sweep of %s failed: %s", target.label, exc)
                errors.append(f"{target.label}: {exc}")

        with self._lock:
            self._events.extend(found)
        self.last_swept_at = self._clock()
        self.last_error = "; ".join(errors) or None

        if found:
            fresh = sum(1 for finding in found if finding.is_fresh)
            logger.info(
                "Swept %d target(s): %d new deal(s), %d posted in the last %d minutes",
                len(self.config.targets),
                len(found),
                fresh,
                FRESH_SECONDS // 60,
            )
            self._publish(found)
        return found


async def run_watch_loop(watcher: DealWatcher, notifier=None) -> None:
    """Sweep on the configured interval until cancelled."""
    while True:
        interval = max(15.0, watcher.config.interval)
        if not watcher.config.enabled:
            await asyncio.sleep(interval)
            continue

        try:
            findings = await asyncio.to_thread(watcher.sweep)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - the loop has to outlive any failure
            logger.exception("Watch sweep failed")
            findings = []

        if findings and notifier is not None:
            try:
                await asyncio.to_thread(notifier, findings)
            except Exception:  # noqa: BLE001
                logger.exception("Notifying about findings failed")

        await asyncio.sleep(interval)
