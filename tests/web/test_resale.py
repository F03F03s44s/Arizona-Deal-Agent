"""Free-pile resale estimates stay conservative and offline."""

from app.craigslist import Listing
from app.resale import estimate_resale, free_listings_to_deals


def test_working_tv_has_a_resale_floor():
    assert estimate_resale("Free 55 inch Samsung TV") >= 60


def test_broken_items_are_worth_nothing():
    assert estimate_resale("Free washer not working") == 0
    assert estimate_resale("Dryer for parts only") == 0


def test_unknown_junk_is_not_treated_as_a_return():
    assert estimate_resale("free bag of clothes") == 0


def test_free_listings_keep_only_high_return_titles():
    listings = [
        Listing("1", "Free 55 inch TV", 1, "https://www.craigslist.org/view/d/tv/1"),
        Listing("2", "Broken chair for parts only", 1, "https://www.craigslist.org/view/d/chair/2"),
        Listing("3", "free bag of clothes", 1, "https://www.craigslist.org/view/d/clothes/3"),
    ]
    deals = free_listings_to_deals(listings)
    assert [deal.id for deal in deals] == ["cl-1"]
    assert deals[0].acquisition_cost == 1
    assert deals[0].market_value >= 60
    assert deals[0].source_label.startswith("Craigslist free")
