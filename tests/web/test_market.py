"""Tests for estimating market value from comparable listings."""

from __future__ import annotations

from app.market import listings_to_deals, title_tokens
from tests.web.conftest import make_listing


def test_title_tokens_drop_filler_words():
    tokens = title_tokens("Like new DeWalt cordless DRILL for sale - $$$")
    assert tokens == frozenset({"dewalt", "cordless", "drill"})


def test_market_value_is_the_median_of_comparables(sample_listings):
    deals = {deal.id: deal for deal in listings_to_deals(sample_listings)}

    # The bargain drill's comparables are the other four drills: 200, 220,
    # 240, 260 -> median 230.
    bargain = deals["cl-bargain"]
    assert bargain.acquisition_cost == 40
    assert bargain.market_value == 230
    assert bargain.comparable_count == 4


def test_listings_without_comparables_are_dropped(sample_listings):
    deal_ids = {deal.id for deal in listings_to_deals(sample_listings)}

    # The circular saw shares no meaningful word with the drills, so there is
    # nothing to price it against.
    assert "cl-saw" not in deal_ids
    assert len(deal_ids) == 5


def test_placeholder_prices_are_ignored():
    listings = [
        make_listing("a", "Milwaukee impact wrench", 300),
        make_listing("b", "Milwaukee impact wrench", 320),
        make_listing("c", "Milwaukee impact wrench", 340),
        make_listing("d", "Milwaukee impact wrench", 360),
        make_listing("cheap", "Milwaukee impact wrench", 1),
    ]
    deals = listings_to_deals(listings)

    assert {deal.id for deal in deals} == {"cl-a", "cl-b", "cl-c", "cl-d"}


def test_deals_carry_listing_provenance(sample_listings):
    deals = {deal.id: deal for deal in listings_to_deals(sample_listings, category="drills")}

    bargain = deals["cl-bargain"]
    assert bargain.source == "craigslist"
    assert bargain.category == "drills"
    assert bargain.location == "Mesa"
    assert bargain.url.startswith("https://www.craigslist.org/view/d/")


def test_too_few_listings_yield_no_deals():
    assert listings_to_deals([make_listing("only", "Lonely hammer drill", 100)]) == []
