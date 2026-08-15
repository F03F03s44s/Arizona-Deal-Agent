from __future__ import annotations

import pytest

from arizona_deal_agent.market import MarketData, ZipMarket
from arizona_deal_agent.models import Assumptions, DealInputs, Listing


@pytest.fixture
def market() -> MarketData:
    """A small fixed market so scores do not move when the snapshot is refreshed."""
    zips = {
        "85041": ZipMarket("85041", "Phoenix", "Maricopa County", "Phoenix, AZ", 360000.0, 2200.0),
        "85713": ZipMarket("85713", "Tucson", "Pima County", "Tucson, AZ", 240000.0, 1400.0),
        "86001": ZipMarket("86001", "Flagstaff", "Coconino County", "Flagstaff, AZ", 675000.0, 2000.0),
        # Value but no rent: exercises the statewide-yield fallback.
        "85739": ZipMarket("85739", "Saddlebrooke", "Pinal County", "Phoenix, AZ", 470000.0, None),
    }
    cities = {
        "phoenix": ZipMarket("", "Phoenix", "Maricopa County", "Phoenix, AZ", 420000.0, 1540.0),
    }
    return MarketData(
        zips=zips,
        cities=cities,
        generated_at="2026-06-30",
        value_as_of="2026-06-30",
        rent_as_of="2026-06-30",
        median_value=400000.0,
        median_rent=1800.0,
    )


@pytest.fixture
def assumptions() -> Assumptions:
    return Assumptions()


@pytest.fixture
def inputs() -> DealInputs:
    """A hand-checked deal used across the finance and scoring tests."""
    return DealInputs(
        price=200_000.0,
        monthly_rent=1_800.0,
        market_value=250_000.0,
        rehab_cost=10_000.0,
        annual_taxes=1_240.0,
        annual_insurance=700.0,
        monthly_hoa=0.0,
        provenance={"price": "listed", "rent": "listed", "market_value": "listed"},
    )


@pytest.fixture
def listing() -> Listing:
    return Listing(
        id="AZ-TEST",
        source="test",
        address="1 Test St",
        city="Phoenix",
        zip_code="85041",
        list_price=300_000.0,
        monthly_rent=2_200.0,
    )


@pytest.fixture
def listings_csv(tmp_path):
    """A CSV that also exercises loose column names and $-formatted money."""
    path = tmp_path / "listings.csv"
    path.write_text(
        "MLS,Street Address,City,Zip,Price,Rent,ARV,Rehab,HOA\n"
        "M-1,100 Good St,Tucson,85713,\"$180,000\",1450,240000,10000,0\n"
        "M-2,200 Meh Ave,Phoenix,85041,\"$355,000\",2100,360000,0,55\n"
        "M-3,300 Bad Blvd,Flagstaff,86001,\"$690,000\",2000,675000,25000,0\n",
        encoding="utf-8",
    )
    return path


HUD_FEATURE = {
    "attributes": {
        "CASE_NUM": "023-123456",
        "CASE_STEP_NUMBER": 6,
        "STREET_NUM": "1234 ",
        "DIRECTION_PREFIX": None,
        "STREET_NAME": "W EXAMPLE RD                  ",
        "CITY": "PHOENIX",
        "STATE_CODE": "AZ",
        "DISPLAY_ZIP_CODE": 85041,
        "MAP_LATITUDE": 33.4,
        "MAP_LONGITUDE": -112.1,
        "DATE_ACQUIRED": 1584576000000,
        "DATE_CLOSED": None,
        "ADDRESS": "1234 W EXAMPLE RD                 ",
    }
}


@pytest.fixture
def hud_payload() -> dict:
    return {"features": [HUD_FEATURE]}
