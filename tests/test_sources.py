"""Discovery sources: file parsing, the live HUD feed, and the registry."""

from __future__ import annotations

import json

import pytest

from arizona_deal_agent import sources
from arizona_deal_agent.sources import FileSource, SourceError, collect, resolve
from arizona_deal_agent.sources import hud_reo as hud_module
from arizona_deal_agent.sources.base import parse_money
from arizona_deal_agent.sources.hud_reo import HudReoSource


@pytest.mark.parametrize(
    "raw,expected",
    [("$385,000", 385000.0), ("385000", 385000.0), (385000, 385000.0), ("", None), ("N/A", None), (None, None)],
)
def test_parse_money(raw, expected):
    assert parse_money(raw) == expected


def test_csv_loads_with_loose_column_names(listings_csv):
    listings = FileSource(listings_csv).fetch()

    assert len(listings) == 3
    first = listings[0]
    assert first.id == "M-1"
    assert first.address == "100 Good St"
    assert first.zip_code == "85713"
    assert first.list_price == 180_000
    assert first.monthly_rent == 1_450
    assert first.market_value == 240_000
    assert first.rehab_cost == 10_000


def test_csv_keeps_unknown_columns_on_detail(tmp_path):
    path = tmp_path / "extra.csv"
    path.write_text("id,price,rent,agent_note\nX-1,200000,1500,call first\n", encoding="utf-8")
    listing = FileSource(path).fetch()[0]
    assert listing.detail["agent_note"] == "call first"


def test_json_list_loads(tmp_path):
    path = tmp_path / "listings.json"
    path.write_text(
        json.dumps([{"id": "J-1", "address": "5 Json Way", "zip": "85041", "price": 250000, "rent": 1800}]),
        encoding="utf-8",
    )
    listing = FileSource(path).fetch()[0]
    assert listing.id == "J-1"
    assert listing.list_price == 250_000


def test_json_wrapped_in_a_key_loads(tmp_path):
    path = tmp_path / "wrapped.json"
    path.write_text(json.dumps({"listings": [{"id": "J-2", "price": 1, "rent": 1}]}), encoding="utf-8")
    assert FileSource(path).fetch()[0].id == "J-2"


def test_missing_file_raises_source_error(tmp_path):
    with pytest.raises(SourceError, match="no such listings file"):
        FileSource(tmp_path / "absent.csv").fetch()


def test_unsupported_file_type_raises(tmp_path):
    path = tmp_path / "listings.xlsx"
    path.write_text("nope", encoding="utf-8")
    with pytest.raises(SourceError, match="unsupported"):
        FileSource(path).fetch()


def test_limit_is_respected(listings_csv):
    assert len(FileSource(listings_csv).fetch(limit=2)) == 2


def test_hud_source_maps_the_feed_onto_listings(monkeypatch, hud_payload):
    monkeypatch.setattr(hud_module, "http_get_json", lambda *a, **k: hud_payload)
    listing = HudReoSource().fetch()[0]

    assert listing.id == "HUD-023-123456"
    assert listing.source == "hud-reo"
    assert listing.address == "1234 W Example Rd"
    assert listing.city == "Phoenix"
    assert listing.zip_code == "85041"
    assert listing.status == "Listed for sale"
    assert listing.latitude == pytest.approx(33.4)
    assert listing.detail["acquired"] == "2020-03-19"
    # The feed publishes no money, which is what enrichment exists for.
    assert listing.list_price is None
    assert listing.monthly_rent is None


def test_hud_query_narrows_to_listed_homes_by_default():
    assert "CASE_STEP_NUMBER=6" in HudReoSource()._where()
    assert "CASE_STEP_NUMBER<=6" in HudReoSource(listed_only=False)._where()
    assert "STATE_CODE='AZ'" in HudReoSource()._where()


def test_hud_service_errors_are_surfaced(monkeypatch):
    monkeypatch.setattr(
        hud_module, "http_get_json", lambda *a, **k: {"error": {"message": "layer offline"}}
    )
    with pytest.raises(SourceError, match="layer offline"):
        HudReoSource().fetch()


def test_hud_rows_without_a_case_number_are_dropped(monkeypatch):
    monkeypatch.setattr(hud_module, "http_get_json", lambda *a, **k: {"features": [{"attributes": {}}]})
    assert HudReoSource().fetch() == []


def test_resolve_accepts_builtins_paths_and_the_file_prefix(listings_csv):
    assert resolve("sample").name == "sample"
    assert resolve("hud-reo").name == "hud-reo"
    assert resolve(str(listings_csv)).path == listings_csv
    assert resolve(f"file:{listings_csv}").path == listings_csv


def test_resolve_rejects_nonsense():
    with pytest.raises(SourceError, match="unknown source"):
        resolve("zillow")


def test_bundled_sample_listings_load():
    listings = sources.SampleSource().fetch()
    assert len(listings) >= 10
    assert all(listing.list_price and listing.monthly_rent for listing in listings)
    assert all(listing.state == "AZ" for listing in listings)


def test_collect_keeps_going_when_one_source_fails(listings_csv):
    results = collect([str(listings_csv), "not-a-source"])

    assert results[0].ok and len(results[0].listings) == 3
    assert not results[1].ok
    assert "unknown source" in results[1].error
