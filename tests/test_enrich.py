"""Gap filling, and the provenance tags that keep estimates visible."""

from __future__ import annotations

from dataclasses import replace

import pytest

from arizona_deal_agent.enrich import AZ_AVERAGE, LISTED, STATE_YIELD, ZHVI, ZORI, enrich
from arizona_deal_agent.models import Listing


def test_listed_numbers_are_kept_and_tagged(market, listing):
    result = enrich(listing, market)

    assert result.inputs.price == 300_000
    assert result.inputs.monthly_rent == 2_200
    assert result.inputs.provenance["price"] == LISTED
    assert result.inputs.provenance["rent"] == LISTED


def test_missing_price_falls_back_to_the_zip_typical_value(market):
    bare = Listing(id="HUD-1", source="hud-reo", address="1 Any St", city="Phoenix", zip_code="85041")
    result = enrich(bare, market)

    assert result.inputs.price == 360_000
    assert result.inputs.market_value == 360_000
    assert result.inputs.provenance["price"] == ZHVI
    assert result.inputs.provenance["market_value"] == ZHVI
    assert result.inputs.is_fully_estimated


def test_missing_rent_comes_from_zori(market):
    bare = Listing(id="HUD-1", source="hud-reo", zip_code="85713", city="Tucson")
    result = enrich(bare, market)

    assert result.inputs.monthly_rent == 1_400
    assert result.inputs.provenance["rent"] == ZORI


def test_rent_falls_back_to_statewide_yield_when_zori_is_missing(market):
    """85739 has a value but no rent, so rent is derived from the state yield."""
    bare = Listing(id="HUD-2", source="hud-reo", zip_code="85739")
    result = enrich(bare, market)

    statewide_yield = (market.median_rent * 12) / market.median_value
    assert result.inputs.monthly_rent == pytest.approx(470_000 * statewide_yield / 12)
    assert result.inputs.provenance["rent"] == STATE_YIELD


def test_unknown_zip_falls_back_to_the_city_median(market):
    bare = Listing(id="X", source="test", city="Phoenix", zip_code="99999")
    result = enrich(bare, market)

    assert result.inputs.market_value == 420_000
    assert result.scope == "Phoenix city median"


def test_unknown_location_falls_back_to_the_state_median(market):
    bare = Listing(id="X", source="test", city="Nowhere", zip_code="00000")
    result = enrich(bare, market)

    assert result.inputs.market_value == market.median_value
    assert result.scope == "Arizona statewide"


def test_carrying_costs_are_estimated_from_arizona_averages(market, listing):
    result = enrich(listing, market)

    assert result.inputs.annual_taxes == pytest.approx(300_000 * 0.0062)
    assert result.inputs.annual_insurance == pytest.approx(300_000 * 0.0035)
    assert result.inputs.provenance["carrying_costs"] == AZ_AVERAGE


def test_supplied_carrying_costs_win(market, listing):
    with_taxes = replace(listing, annual_taxes=2_500.0, annual_insurance=900.0)
    result = enrich(with_taxes, market)

    assert result.inputs.annual_taxes == 2_500
    assert result.inputs.provenance["carrying_costs"] == LISTED


def test_market_scope_names_the_zip_that_was_used(market, listing):
    assert enrich(listing, market).inputs.provenance["market_scope"] == "ZIP 85041"


def test_a_listed_arv_is_preferred_over_zhvi(market, listing):
    with_arv = replace(listing, market_value=410_000.0)
    result = enrich(with_arv, market)

    assert result.inputs.market_value == 410_000
    assert result.inputs.provenance["market_value"] == LISTED
    # The price was listed too, so it must not inherit the ARV.
    assert result.inputs.price == 300_000
