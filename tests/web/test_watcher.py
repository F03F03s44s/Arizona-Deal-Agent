"""Tests for the background scan that reports newly-posted deals."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.craigslist import CraigslistError, Listing, SearchResult
from app.sources import WatchTarget
from app.watcher import DealWatcher, WatchConfig
from tests.web.conftest import make_listing

NOW = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)


def aged(posting_id: str, price: float, minutes: float) -> Listing:
    listing = make_listing(posting_id, "DeWalt cordless drill", price)
    return Listing(
        posting_id=listing.posting_id,
        title=listing.title,
        price=listing.price,
        url=listing.url,
        location=listing.location,
        posted_at=NOW - timedelta(minutes=minutes),
        category_id=118,
    )


# Four drills setting a 230 median, so anything near 40 is an obvious bargain.
BACKLOG = [aged("a", 200, 600), aged("b", 220, 600), aged("c", 240, 600), aged("d", 260, 600)]


def watcher_over(batches, *, cache_ts=None, **config) -> DealWatcher:
    """A watcher whose source hands back ``batches`` one sweep at a time.

    Each batch gets its own cache timestamp by default, so the source looks
    like it refreshed between sweeps.
    """
    calls = {"n": 0}

    def fetcher(target, limit=None):
        index = min(calls["n"], len(batches) - 1)
        stamp = cache_ts if cache_ts is not None else 1_786_000_000 + calls["n"]
        calls["n"] += 1
        return SearchResult(listings=batches[index], cache_ts=stamp)

    settings = {"targets": [WatchTarget()], "min_score": 0.9, "budget": 15000}
    settings.update(config)
    return DealWatcher(WatchConfig(**settings), fetcher=fetcher, clock=lambda: NOW)


def test_first_sweep_is_silent():
    watcher = watcher_over([BACKLOG])

    # Announcing the entire existing backlog on startup would be noise, not news.
    assert watcher.sweep() == []


def test_second_sweep_reports_only_what_is_new():
    watcher = watcher_over([BACKLOG, BACKLOG + [aged("steal", 40, 2)]])
    watcher.sweep()

    findings = watcher.sweep()

    assert [f.scored.deal.id for f in findings] == ["cl-steal"]
    assert findings[0].scored.score >= 0.9


def test_new_listings_are_priced_against_the_whole_cohort():
    watcher = watcher_over([BACKLOG, BACKLOG + [aged("steal", 40, 2)]])
    watcher.sweep()

    (finding,) = watcher.sweep()

    # Median of the four backlog drills, not of the one new listing.
    assert finding.scored.deal.market_value == 230
    assert finding.scored.deal.comparable_count == 4


def test_recent_arrivals_are_flagged_as_just_posted():
    watcher = watcher_over([BACKLOG, BACKLOG + [aged("steal", 40, 2), aged("older", 45, 400)]])
    watcher.sweep()

    findings = {f.scored.deal.id: f for f in watcher.sweep()}

    assert findings["cl-steal"].age_seconds == pytest.approx(120)
    assert findings["cl-steal"].is_fresh is True
    assert findings["cl-older"].is_fresh is False


def test_listings_below_the_threshold_are_not_reported():
    watcher = watcher_over([BACKLOG, BACKLOG + [aged("meh", 225, 2)]])
    watcher.sweep()

    assert watcher.sweep() == []


def test_over_budget_finds_are_not_reported():
    watcher = watcher_over([BACKLOG, BACKLOG + [aged("steal", 40, 2)]], budget=20)
    watcher.sweep()

    assert watcher.sweep() == []


def test_a_listing_is_only_reported_once():
    later = BACKLOG + [aged("steal", 40, 2)]
    watcher = watcher_over([BACKLOG, later, later])
    watcher.sweep()

    assert len(watcher.sweep()) == 1
    assert watcher.sweep() == []


def test_findings_are_kept_for_late_joiners():
    watcher = watcher_over([BACKLOG, BACKLOG + [aged("steal", 40, 2)]])
    watcher.sweep()
    watcher.sweep()

    assert [f.scored.deal.id for f in watcher.recent()] == ["cl-steal"]


def test_a_failing_target_does_not_stop_the_sweep():
    def fetcher(target, limit=None):
        if target.category == "rea":
            raise CraigslistError("403 blocked")
        return SearchResult(listings=BACKLOG, cache_ts=1)

    watcher = DealWatcher(
        WatchConfig(targets=[WatchTarget(category="rea"), WatchTarget(category="sss")]),
        fetcher=fetcher,
        clock=lambda: NOW,
    )
    watcher.sweep()

    assert watcher.last_error is not None
    assert "403 blocked" in watcher.last_error
    assert watcher.last_swept_at == NOW


def test_each_target_tracks_what_it_has_seen_separately():
    seen_targets = []

    def fetcher(target, limit=None):
        seen_targets.append(target.category)
        listings = BACKLOG if len(seen_targets) <= 2 else BACKLOG + [aged("steal", 40, 2)]
        return SearchResult(listings=listings, cache_ts=len(seen_targets))

    watcher = DealWatcher(
        WatchConfig(
            targets=[WatchTarget(category="sss"), WatchTarget(category="rea")],
            min_score=0.9,
            budget=15000,
        ),
        fetcher=fetcher,
        clock=lambda: NOW,
    )
    watcher.sweep()
    findings = watcher.sweep()

    # The same new listing appears under both targets, and both report it.
    assert len(findings) == 2
    assert {f.target_label for f in findings} == {
        "Phoenix - All for sale",
        "Phoenix - Real estate for sale",
    }


@pytest.mark.parametrize("prime_first", [True])
def test_findings_are_pushed_to_subscribers(prime_first):
    async def scenario():
        watcher = watcher_over([BACKLOG, BACKLOG + [aged("steal", 40, 2)]])
        watcher.sweep()

        queue = watcher.subscribe()
        await asyncio.to_thread(watcher.sweep)
        finding = await asyncio.wait_for(queue.get(), timeout=2)

        assert finding.scored.deal.id == "cl-steal"
        watcher.unsubscribe(queue)

        # Once unsubscribed the queue must stop receiving.
        await asyncio.to_thread(watcher.sweep)
        assert queue.empty()

    asyncio.run(scenario())


def test_an_unrefreshed_source_is_not_reprocessed():
    # Craigslist answers this search from a cache that only rolls every ~15
    # minutes. Between rolls the response is identical, so there is nothing to
    # look at even if the sweep interval is far shorter.
    watcher = watcher_over([BACKLOG, BACKLOG + [aged("steal", 40, 2)]], cache_ts=777)
    watcher.sweep()

    assert watcher.sweep() == []
    assert watcher.source_refreshed_at is not None


def test_a_refreshed_source_is_processed():
    watcher = watcher_over([BACKLOG, BACKLOG + [aged("steal", 40, 2)]])
    watcher.sweep()

    assert len(watcher.sweep()) == 1


def test_source_refresh_time_is_reported():
    watcher = watcher_over([BACKLOG], cache_ts=1_786_000_000)
    watcher.sweep()

    assert watcher.source_refreshed_at == datetime.fromtimestamp(1_786_000_000, tz=UTC)


def test_findings_serialise_for_the_event_stream():
    watcher = watcher_over([BACKLOG, BACKLOG + [aged("steal", 40, 2)]])
    watcher.sweep()
    (finding,) = watcher.sweep()

    payload = finding.as_dict()

    assert payload["deal"]["deal"]["title"] == "DeWalt cordless drill"
    assert payload["is_fresh"] is True
    assert payload["target_label"] == "Phoenix - All for sale"
    assert payload["age_seconds"] == pytest.approx(120)
