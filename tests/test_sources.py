import textwrap

import pytest

from deal_agent.sources import load_csv, load_sample

REDFIN_STYLE_CSV = textwrap.dedent(
    """\
    SALE TYPE,SOLD DATE,PROPERTY TYPE,ADDRESS,CITY,STATE OR PROVINCE,ZIP OR POSTAL CODE,PRICE,BEDS,BATHS,LOCATION,SQUARE FEET,LOT SIZE,YEAR BUILT,DAYS ON MARKET,$/SQUARE FEET,HOA/MONTH,STATUS,URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)
    MLS Listing,,Single Family Residential,742 W Vista Dr,Phoenix,AZ,85021,"415,000",3,2,Alhambra,"1,550","7,200",1998,41,268,,Active,https://www.redfin.com/AZ/example-1
    MLS Listing,,Condo/Co-op,100 E Rio Salado Pkwy #204,Tempe,AZ,85281,"329,900",2,2,Downtown Tempe,980,,2007,12,337,285,Active,https://www.redfin.com/AZ/example-2
    MLS Listing,,Vacant Land,0 N Desert Rd,Buckeye,AZ,85326,"90,000",,,Rural,,,,,,,Active,https://www.redfin.com/AZ/example-3
    """
)

OWN_FORMAT_CSV = textwrap.dedent(
    """\
    address,city,price,beds,baths,sqft,year_built,days_on_market,property_type
    1 Main St,Mesa,350000,3,2,1400,2001,30,single_family
    2 Bad Row,Mesa,,3,2,1400,2001,30,single_family
    """
)


def test_load_sample_dataset():
    listings = load_sample()
    assert len(listings) >= 50
    assert all(l.state == "AZ" for l in listings)
    assert all(l.price > 0 for l in listings)
    assert len({l.city for l in listings}) >= 10


def test_load_redfin_style_csv(tmp_path):
    path = tmp_path / "redfin.csv"
    path.write_text(REDFIN_STYLE_CSV)
    listings = load_csv(path)
    assert len(listings) == 3

    house = listings[0]
    assert house.city == "Phoenix"
    assert house.price == 415_000
    assert house.sqft == 1550
    assert house.lot_sqft == 7200
    assert house.days_on_market == 41
    assert house.property_type == "single_family"
    assert house.url and house.url.startswith("https://www.redfin.com")

    condo = listings[1]
    assert condo.property_type == "condo"
    assert condo.hoa_monthly == 285

    land = listings[2]
    assert land.property_type == "land"
    assert land.sqft is None


def test_load_own_format_csv_skips_rows_without_price(tmp_path):
    path = tmp_path / "own.csv"
    path.write_text(OWN_FORMAT_CSV)
    listings = load_csv(path)
    assert len(listings) == 1
    assert listings[0].city == "Mesa"


def test_unrecognizable_csv_raises(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("foo,bar\n1,2\n")
    with pytest.raises(ValueError, match="missing a recognizable"):
        load_csv(path)
