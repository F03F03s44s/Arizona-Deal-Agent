from pathlib import Path

import pytest

from arizona_deal_agent.models import Assumptions, Listing

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV = PROJECT_ROOT / "data" / "sample_listings.csv"


@pytest.fixture
def assumptions() -> Assumptions:
    """Package defaults, stated explicitly so tests do not drift with them."""
    return Assumptions(
        down_payment_pct=0.20,
        interest_rate=0.065,
        loan_term_years=30,
        closing_cost_pct=0.03,
        vacancy_rate=0.06,
        maintenance_rate=0.08,
        management_rate=0.08,
        flip_rule_pct=0.70,
    )


@pytest.fixture
def listing() -> Listing:
    """Round numbers chosen so every metric can be checked by hand."""
    return Listing(
        id="TEST-1",
        address="1 Test Way",
        city="Phoenix",
        list_price=300_000,
        monthly_rent=2_000,
        annual_taxes=2_400,
        annual_insurance=1_200,
        monthly_hoa=100,
    )


@pytest.fixture
def sample_csv() -> Path:
    return SAMPLE_CSV
