"""Tests for watch targets and the source registry."""

from __future__ import annotations

import pytest

from app import sources
from app.craigslist import CraigslistError
from app.sources import AREAS, DEFAULT_TARGETS, WatchTarget


def test_targets_are_identified_by_every_filter():
    base = WatchTarget(area_id=18, category="sss", query="drill", seller_type=None)

    assert base.key == WatchTarget(area_id=18, category="sss", query="Drill").key
    assert base.key != WatchTarget(area_id=57, category="sss", query="drill").key
    assert base.key != WatchTarget(area_id=18, category="rea", query="drill").key
    assert base.key != WatchTarget(area_id=18, category="sss", query="drill", seller_type="dealer").key


def test_targets_describe_themselves_in_words():
    target = WatchTarget(area_id=57, category="rea", query="fixer", seller_type="dealer")

    assert target.label == 'Tucson - Real estate for sale - "fixer" - dealers only'
    assert target.is_property is True


def test_goods_targets_are_not_property():
    assert WatchTarget(category="sss").is_property is False
    assert WatchTarget(category="tla").is_property is False


def test_every_arizona_area_is_watchable():
    assert AREAS[18] == "Phoenix"
    assert len(AREAS) == 8


def test_default_targets_cover_goods_and_property():
    kinds = {target.is_property for target in DEFAULT_TARGETS}
    assert kinds == {True, False}


def test_fetch_routes_through_the_named_source(monkeypatch):
    captured = {}

    class FakeSource:
        name = "craigslist"
        label = "Craigslist"

        def fetch(self, target, *, limit):
            captured["target"] = target
            captured["limit"] = limit
            return []

    monkeypatch.setitem(sources.SOURCES, "craigslist", FakeSource())
    target = WatchTarget(area_id=244, category="rea")
    sources.fetch(target, limit=10)

    assert captured["target"] is target
    assert captured["limit"] == 10


def test_unknown_sources_are_rejected():
    with pytest.raises(CraigslistError, match="Unknown source"):
        sources.fetch(WatchTarget(source="zillow"))
