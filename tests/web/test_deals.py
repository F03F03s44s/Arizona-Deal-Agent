"""Tests for the sourcing layer: scrape once, then serve from cache."""

from __future__ import annotations

from app.craigslist import CraigslistError
from app.deals import DealService
from tests.web.conftest import make_listing

LISTINGS = [
    make_listing("1", "Ryobi table saw", 200),
    make_listing("2", "Ryobi table saw", 240),
    make_listing("3", "Ryobi table saw", 280),
    make_listing("4", "Ryobi table saw", 60),
]


def _service(searcher) -> DealService:
    return DealService(searcher=searcher)


def test_repeated_reads_scrape_once():
    calls = []

    def searcher(query, **kwargs):
        calls.append(query)
        return LISTINGS

    service = _service(searcher)
    first = service.get_deals("table saw")
    second = service.get_deals("table saw")

    assert len(calls) == 1
    assert first.source == "craigslist"
    assert [d.id for d in second.deals] == [d.id for d in first.deals]


def test_queries_are_cached_case_insensitively():
    calls = []

    def searcher(query, **kwargs):
        calls.append(query)
        return LISTINGS

    service = _service(searcher)
    service.get_deals("Table Saw")
    service.get_deals("table saw")

    assert len(calls) == 1


def test_refresh_forces_a_new_scrape():
    calls = []

    def searcher(query, **kwargs):
        calls.append(query)
        return LISTINGS

    service = _service(searcher)
    service.get_deals("table saw")
    service.get_deals("table saw", refresh=True)

    assert len(calls) == 2


def test_expired_entries_are_refetched():
    calls = []

    def searcher(query, **kwargs):
        calls.append(query)
        return LISTINGS

    service = DealService(searcher=searcher, ttl=0)
    service.get_deals("table saw")
    service.get_deals("table saw")

    assert len(calls) == 2


def test_scrape_failure_falls_back_to_sample_deals():
    def searcher(query, **kwargs):
        raise CraigslistError("Craigslist request failed: 403")

    sourced = _service(searcher).get_deals("table saw")

    assert sourced.source == "sample"
    assert sourced.deals
    assert "Craigslist unavailable" in (sourced.warning or "")


def test_failures_are_not_cached():
    attempts = []

    def searcher(query, **kwargs):
        attempts.append(query)
        raise CraigslistError("down")

    service = _service(searcher)
    service.get_deals("table saw")
    service.get_deals("table saw")

    assert len(attempts) == 2


def test_unpriceable_results_fall_back_to_sample_deals():
    def searcher(query, **kwargs):
        return [make_listing("solo", "One of a kind widget", 500)]

    sourced = _service(searcher).get_deals("widget")

    assert sourced.source == "sample"
    assert "No priced Craigslist listings" in (sourced.warning or "")
