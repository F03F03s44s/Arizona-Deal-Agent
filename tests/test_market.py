"""Market snapshot loading, lookup, and regeneration."""

from __future__ import annotations

import json

from arizona_deal_agent import market as market_module
from arizona_deal_agent.market import build_snapshot, from_payload, load_snapshot, write_snapshot

ZHVI_ROWS = [
    {"RegionName": "85041", "State": "AZ", "City": "Phoenix", "CountyName": "Maricopa County",
     "Metro": "Phoenix, AZ", "2026-05-31": "355000", "2026-06-30": "360000"},
    {"RegionName": "85713", "State": "AZ", "City": "Tucson", "CountyName": "Pima County",
     "Metro": "Tucson, AZ", "2026-05-31": "238000", "2026-06-30": "240000"},
    {"RegionName": "90210", "State": "CA", "City": "Beverly Hills", "CountyName": "Los Angeles County",
     "Metro": "Los Angeles, CA", "2026-05-31": "1", "2026-06-30": "5000000"},
]

ZORI_ROWS = [
    {"RegionName": "85041", "State": "AZ", "City": "Phoenix", "CountyName": "Maricopa County",
     "Metro": "Phoenix, AZ", "2026-05-31": "2150", "2026-06-30": "2200"},
    {"RegionName": "85713", "State": "AZ", "City": "Tucson", "CountyName": "Pima County",
     "Metro": "Tucson, AZ", "2026-05-31": "1380", "2026-06-30": ""},
]


def fake_reader(url):
    return iter(ZORI_ROWS if "zori" in url else ZHVI_ROWS)


def test_build_snapshot_filters_to_one_state_and_takes_the_latest_month():
    payload = build_snapshot(state="AZ", reader=fake_reader)

    assert set(payload["zips"]) == {"85041", "85713"}
    assert payload["zips"]["85041"]["value"] == 360000.0
    assert payload["zips"]["85041"]["rent"] == 2200.0
    assert payload["value_as_of"] == "2026-06-30"


def test_build_snapshot_skips_blank_months():
    """Tucson's newest rent cell is empty, so the month before it is used."""
    payload = build_snapshot(state="AZ", reader=fake_reader)
    assert payload["zips"]["85713"]["rent"] == 1380.0
    # The published vintage stays at the newest month any row reported.
    assert payload["rent_as_of"] == "2026-06-30"


def test_city_medians_are_derived_from_the_zips():
    payload = build_snapshot(state="AZ", reader=fake_reader)
    assert payload["cities"]["phoenix"]["value"] == 360000.0
    assert payload["cities"]["tucson"]["rent"] == 1380.0


def test_round_trip_through_disk(tmp_path):
    payload = build_snapshot(state="AZ", reader=fake_reader)
    path = write_snapshot(payload, tmp_path / "snap.json")
    data = load_snapshot(path)

    assert data.zips["85041"].typical_value == 360000.0
    assert data.zips["85041"].city == "Phoenix"
    assert data.median_value == 300000.0  # median of 360000 and 240000


def test_lookup_prefers_zip_then_city_then_nothing(market):
    assert market.lookup("85041").city == "Phoenix"
    assert market.lookup("99999", "Phoenix").typical_value == 420000.0
    assert market.lookup("99999", "Nowhere") is None


def test_lookup_tolerates_messy_zip_input(market):
    assert market.lookup("85041-1234").zip_code == "85041"
    assert market.lookup(" 85041 ").zip_code == "85041"


def test_missing_snapshot_file_yields_an_empty_market(tmp_path):
    data = load_snapshot(tmp_path / "absent.json")
    assert data.zips == {}
    assert data.lookup("85041") is None


def test_rent_to_value(market):
    assert market.zips["85041"].rent_to_value == (2200 * 12) / 360000
    assert market.zips["85739"].rent_to_value is None


def test_packaged_snapshot_is_present_and_covers_arizona():
    data = load_snapshot()
    assert len(data.zips) > 100
    assert data.value_as_of
    phoenix = data.lookup("", "Phoenix")
    assert phoenix and phoenix.typical_value and phoenix.typical_value > 0


def test_from_payload_handles_partial_rows():
    data = from_payload({"zips": {"85041": {"city": "Phoenix", "value": 360000.0}}})
    assert data.zips["85041"].typical_rent is None
    assert data.zips["85041"].typical_value == 360000.0


def test_snapshot_on_disk_is_valid_json():
    with market_module.SNAPSHOT_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    assert payload["state"] == "AZ"
    assert payload["sources"]
