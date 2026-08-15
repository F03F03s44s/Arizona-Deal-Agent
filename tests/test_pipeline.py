"""The find -> enrich -> underwrite -> rank pipeline."""

from __future__ import annotations

import pytest

from arizona_deal_agent.models import Budget, Listing
from arizona_deal_agent.pipeline import SearchRequest, dedupe, search
from arizona_deal_agent.sources import SourceResult


def test_dedupe_merges_the_same_address_from_two_sources():
    unpriced = Listing(id="HUD-1", source="hud-reo", address="1041 S Delaware Dr", zip_code="85120")
    priced = Listing(id="MLS-9", source="mls", address="1041 S DELAWARE DR", zip_code="85120", list_price=250_000)

    merged = dedupe([unpriced, priced])
    assert len(merged) == 1
    assert merged[0].id == "MLS-9"


def test_dedupe_keeps_different_addresses():
    listings = [
        Listing(id="A", source="s", address="1 First St", zip_code="85041"),
        Listing(id="B", source="s", address="2 Second St", zip_code="85041"),
    ]
    assert len(dedupe(listings)) == 2


def test_dedupe_falls_back_to_the_id_when_there_is_no_address():
    listings = [Listing(id="A", source="s"), Listing(id="B", source="s")]
    assert len(dedupe(listings)) == 2


def test_search_ranks_a_file_source(listings_csv, market):
    result = search(SearchRequest(sources=[str(listings_csv)]), market=market)

    assert result.found == 3
    assert len(result.deals) == 3
    assert result.best.listing.id == "M-1"
    scores = [deal.score.composite for deal in result.deals]
    assert scores == sorted(scores, reverse=True)


def test_city_filter_narrows_the_result(listings_csv, market):
    result = search(SearchRequest(sources=[str(listings_csv)], cities=["Tucson"]), market=market)

    assert [deal.listing.city for deal in result.deals] == ["Tucson"]
    assert result.filtered_out == 2


def test_zip_filter_narrows_the_result(listings_csv, market):
    result = search(SearchRequest(sources=[str(listings_csv)], zips=["86001"]), market=market)
    assert [deal.listing.id for deal in result.deals] == ["M-3"]


def test_over_budget_deals_are_hidden_by_default(listings_csv, market):
    request = SearchRequest(sources=[str(listings_csv)], budget=Budget(max_price=200_000))
    result = search(request, market=market)

    assert result.over_budget == 2
    assert [deal.listing.id for deal in result.deals] == ["M-1"]


def test_over_budget_deals_can_be_shown_and_sort_last(listings_csv, market):
    request = SearchRequest(
        sources=[str(listings_csv)], budget=Budget(max_price=200_000), include_over_budget=True
    )
    result = search(request, market=market)

    assert len(result.deals) == 3
    assert result.deals[0].fits_budget
    assert not result.deals[-1].fits_budget


def test_top_trims_the_ranking(listings_csv, market):
    result = search(SearchRequest(sources=[str(listings_csv)], top=2), market=market)
    assert len(result.deals) == 2


def test_a_broken_source_is_reported_without_killing_the_search(listings_csv, market):
    result = search(SearchRequest(sources=[str(listings_csv), "nonsense"]), market=market)

    assert len(result.deals) == 3
    assert any("nonsense" in error for error in result.errors)
    assert [report.ok for report in result.source_reports] == [True, False]


def test_a_search_with_no_candidates_returns_empty(tmp_path, market):
    empty = tmp_path / "empty.csv"
    empty.write_text("id,price,rent\n", encoding="utf-8")
    result = search(SearchRequest(sources=[str(empty)]), market=market)

    assert result.deals == []
    assert result.best is None


def test_live_hud_listings_are_scored_from_market_estimates(monkeypatch, market, hud_payload):
    from arizona_deal_agent.sources import hud_reo as hud_module

    monkeypatch.setattr(hud_module, "http_get_json", lambda *a, **k: hud_payload)
    result = search(SearchRequest(sources=["hud-reo"]), market=market)

    assert len(result.deals) == 1
    deal = result.deals[0]
    assert deal.inputs.price == pytest.approx(360_000)  # ZIP 85041 typical value
    assert deal.inputs.monthly_rent == pytest.approx(2_200)
    assert deal.warnings
    assert deal.breakeven_price > 0


def test_market_vintage_is_carried_into_the_result(listings_csv, market):
    result = search(SearchRequest(sources=[str(listings_csv)]), market=market)
    assert result.market_as_of == "2026-06-30"


def test_source_result_ok_flag():
    assert SourceResult("s", []).ok
    assert not SourceResult("s", [], error="boom").ok
