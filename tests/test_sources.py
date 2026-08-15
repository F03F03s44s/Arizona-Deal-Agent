"""Loading real-world files: messy columns, missing fields, and bad rows."""

import json

import pytest

from arizona_deal_agent.sources import (
    DEFAULT_INSURANCE_RATE,
    DEFAULT_TAX_RATE,
    ListingParseError,
    load_listings,
    parse_number,
    record_to_listing,
)

MINIMAL_CSV = "id,list_price,monthly_rent\nA-1,300000,2000\n"


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


class TestParseNumber:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("385000", 385_000),
            ("$385,000", 385_000),
            (" $385,000.50 ", 385_000.50),
            (385000, 385_000),
            (385000.5, 385_000.5),
            ("6.5%", 0.065),
            ("-250", -250),
        ],
    )
    def test_accepts_the_shapes_spreadsheets_produce(self, raw, expected):
        assert parse_number(raw, "list_price", "row 2") == pytest.approx(expected)

    def test_rejects_text_and_says_where(self):
        with pytest.raises(ListingParseError) as excinfo:
            parse_number("call agent", "list_price", "listings.csv row 4")
        assert "listings.csv row 4" in str(excinfo.value)
        assert "list_price" in str(excinfo.value)


class TestRecordToListing:
    def test_required_fields_are_enough(self):
        listing = record_to_listing({"id": "A-1", "list_price": 300_000, "monthly_rent": 2_000})
        assert listing.id == "A-1"
        assert listing.list_price == 300_000

    def test_missing_fields_are_reported_together(self):
        with pytest.raises(ListingParseError) as excinfo:
            record_to_listing({"id": "A-1"}, where="row 2")
        message = str(excinfo.value)
        assert "list_price" in message and "monthly_rent" in message

    def test_taxes_and_insurance_are_estimated_when_absent(self):
        listing = record_to_listing({"id": "A-1", "list_price": 300_000, "monthly_rent": 2_000})
        assert listing.annual_taxes == pytest.approx(300_000 * DEFAULT_TAX_RATE)
        assert listing.annual_insurance == pytest.approx(300_000 * DEFAULT_INSURANCE_RATE)

    def test_supplied_taxes_are_not_overwritten(self):
        listing = record_to_listing(
            {"id": "A-1", "list_price": 300_000, "monthly_rent": 2_000, "annual_taxes": 99}
        )
        assert listing.annual_taxes == 99

    def test_column_aliases_are_understood(self):
        listing = record_to_listing(
            {
                "ID": "A-1",
                "Price": "$310,000",
                "Rent": "2,100",
                "HOA": "45",
                "Zip": "85051",
                "Rehab": "5000",
                "After Repair Value": "360000",
                "Square Feet": "1,450",
            }
        )
        assert listing.list_price == 310_000
        assert listing.monthly_rent == 2_100
        assert listing.monthly_hoa == 45
        assert listing.zip_code == "85051"
        assert listing.rehab_cost == 5_000
        assert listing.arv == 360_000
        assert listing.sqft == 1_450

    def test_blank_cells_are_treated_as_absent(self):
        listing = record_to_listing(
            {"id": "A-1", "list_price": 300_000, "monthly_rent": 2_000, "arv": "", "monthly_hoa": "  "}
        )
        assert listing.arv is None
        assert listing.monthly_hoa == 0

    def test_invalid_values_surface_as_parse_errors(self):
        with pytest.raises(ListingParseError):
            record_to_listing({"id": "A-1", "list_price": -5, "monthly_rent": 2_000})

    def test_extra_columns_are_ignored(self):
        # MLS exports carry dozens of columns nobody scores on.
        listing = record_to_listing(
            {
                "id": "A-1",
                "list_price": 300_000,
                "monthly_rent": 2_000,
                "pool": "yes",
                "listing_agent": "Dana",
                "photo_url": "http://example.test/1.jpg",
            }
        )
        assert listing.id == "A-1"


class TestLoadCsv:
    def test_reads_the_bundled_sample(self, sample_csv):
        listings = load_listings(sample_csv)
        assert len(listings) == 13
        assert listings[0].id == "AZ-001"
        assert listings[0].city == "Phoenix"
        assert all(listing.list_price > 0 for listing in listings)

    def test_blank_arv_column_becomes_none(self, sample_csv):
        by_id = {listing.id: listing for listing in load_listings(sample_csv)}
        assert by_id["AZ-001"].arv is None
        assert by_id["AZ-011"].arv == 340_000

    def test_only_three_columns_are_required(self, tmp_path):
        listings = load_listings(write(tmp_path, "min.csv", MINIMAL_CSV))
        assert len(listings) == 1
        assert listings[0].annual_taxes > 0

    def test_row_numbers_point_at_the_offending_line(self, tmp_path):
        broken = MINIMAL_CSV + "A-2,not-a-price,1800\n"
        with pytest.raises(ListingParseError) as excinfo:
            load_listings(write(tmp_path, "broken.csv", broken))
        assert "row 3" in str(excinfo.value)

    def test_duplicate_ids_are_refused(self, tmp_path):
        dupes = MINIMAL_CSV + "A-1,280000,1900\n"
        with pytest.raises(ListingParseError) as excinfo:
            load_listings(write(tmp_path, "dupes.csv", dupes))
        assert "A-1" in str(excinfo.value)

    def test_empty_file_is_refused(self, tmp_path):
        with pytest.raises(ListingParseError):
            load_listings(write(tmp_path, "empty.csv", ""))

    def test_byte_order_mark_is_stripped(self, tmp_path):
        path = tmp_path / "bom.csv"
        path.write_bytes(b"\xef\xbb\xbf" + MINIMAL_CSV.encode("utf-8"))
        assert load_listings(path)[0].id == "A-1"


class TestLoadJson:
    def test_reads_a_plain_array(self, tmp_path):
        payload = [{"id": "A-1", "list_price": 300_000, "monthly_rent": 2_000}]
        path = write(tmp_path, "listings.json", json.dumps(payload))
        assert load_listings(path)[0].id == "A-1"

    def test_reads_a_wrapped_object(self, tmp_path):
        payload = {"listings": [{"id": "A-1", "list_price": 300_000, "monthly_rent": 2_000}]}
        path = write(tmp_path, "wrapped.json", json.dumps(payload))
        assert len(load_listings(path)) == 1

    def test_malformed_json_is_reported(self, tmp_path):
        with pytest.raises(ListingParseError) as excinfo:
            load_listings(write(tmp_path, "bad.json", "{nope"))
        assert "invalid JSON" in str(excinfo.value)

    def test_wrong_shape_is_reported(self, tmp_path):
        with pytest.raises(ListingParseError):
            load_listings(write(tmp_path, "scalar.json", "42"))


class TestLoadDispatch:
    def test_missing_file(self, tmp_path):
        with pytest.raises(ListingParseError) as excinfo:
            load_listings(tmp_path / "nope.csv")
        assert "not found" in str(excinfo.value)

    def test_unsupported_extension(self, tmp_path):
        with pytest.raises(ListingParseError) as excinfo:
            load_listings(write(tmp_path, "listings.txt", MINIMAL_CSV))
        assert "unsupported file type" in str(excinfo.value)
