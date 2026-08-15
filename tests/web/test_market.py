"""Tests for estimating market value from comparable listings."""

from __future__ import annotations

from app.craigslist import Listing
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


def test_comparables_an_order_of_magnitude_away_are_ignored():
    listings = [
        make_listing("rent-a", "Casita in Mesa", 1_800),
        make_listing("rent-b", "Casita in Mesa", 1_900),
        make_listing("rent-c", "Casita in Mesa", 2_000),
        make_listing("rent-d", "Casita in Mesa", 2_100),
        make_listing("sale-a", "Casita in Mesa", 400_000),
        make_listing("sale-b", "Casita in Mesa", 420_000),
        make_listing("sale-c", "Casita in Mesa", 440_000),
        make_listing("sale-d", "Casita in Mesa", 460_000),
    ]
    deals = {deal.id: deal for deal in listings_to_deals(listings)}

    # A monthly rent priced against outright sale prices would invent a
    # fortune in margin, so the two groups never see each other.
    assert deals["cl-rent-a"].market_value == 2_000
    assert deals["cl-sale-a"].market_value == 440_000


# -- property ------------------------------------------------------------


def home(posting_id: str, price: float, beds: int, sqft: int):
    """A real-estate listing (Craigslist category 143 is 'real estate')."""
    listing = make_listing(posting_id, f"{beds} bedroom home in Mesa", price)
    return Listing(
        posting_id=listing.posting_id,
        title=listing.title,
        price=listing.price,
        url=listing.url,
        location=listing.location,
        category_id=143,
        bedrooms=beds,
        area_sqft=sqft,
    )


def test_property_is_valued_on_price_per_square_foot():
    listings = [
        home("comp-a", 300_000, 3, 1_500),  # $200/sqft
        home("comp-b", 320_000, 3, 1_600),  # $200/sqft
        home("comp-c", 340_000, 3, 1_700),  # $200/sqft
        home("bargain", 180_000, 3, 1_800),  # $100/sqft on a bigger house
    ]
    deals = {deal.id: deal for deal in listings_to_deals(listings)}

    # The going rate is $200/sqft, so 1,800 sqft is worth $360,000.
    assert deals["cl-bargain"].market_value == 360_000
    assert deals["cl-bargain"].comparable_count == 3


def test_property_only_compares_the_same_bedroom_count():
    listings = [
        home("three-a", 300_000, 3, 1_500),
        home("three-b", 306_000, 3, 1_530),
        home("three-c", 312_000, 3, 1_560),
        home("three-d", 318_000, 3, 1_590),
        home("one-bed", 150_000, 1, 600),
    ]
    deals = {deal.id: deal for deal in listings_to_deals(listings)}

    # The lone one-bedroom has no same-size comparables, so it goes unpriced
    # rather than being measured against three-bedroom houses.
    assert "cl-one-bed" not in deals
    assert "cl-three-a" in deals


def test_land_without_square_footage_is_left_unpriced():
    listings = [
        home("house-a", 300_000, 3, 1_500),
        home("house-b", 320_000, 3, 1_600),
        home("house-c", 340_000, 3, 1_700),
        Listing(
            posting_id="lot",
            title="1 acre lot, build your dream home",
            price=299,
            url="https://www.craigslist.org/view/d/slug/lot",
            category_id=143,
        ),
    ]
    deals = {deal.id: deal for deal in listings_to_deals(listings)}

    # A bare lot has no square footage to compare, and pricing it against
    # houses is how a $299 listing turns into a six-figure "profit".
    assert "cl-lot" not in deals
