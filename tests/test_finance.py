"""Finance math, checked against values computed by hand."""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from arizona_deal_agent.finance import breakeven_price, monthly_payment, underwrite
from arizona_deal_agent.models import Assumptions, DealInputs


@pytest.mark.parametrize(
    "principal,rate,years,expected",
    [
        (200_000, 0.065, 30, 1_264.14),
        (300_000, 0.07, 15, 2_696.48),
        (100_000, 0.0, 30, 277.78),
    ],
)
def test_monthly_payment(principal, rate, years, expected):
    assert monthly_payment(principal, rate, years) == pytest.approx(expected, abs=0.01)


def test_no_loan_means_no_payment():
    assert monthly_payment(0, 0.065, 30) == 0.0


def test_underwriting_matches_hand_calculation(inputs, assumptions):
    numbers = underwrite(inputs, assumptions)

    assert numbers.total_cost_basis == 210_000
    assert numbers.down_payment == 40_000
    assert numbers.loan_amount == 160_000
    assert numbers.closing_costs == 6_000
    assert numbers.cash_to_close == 56_000
    assert numbers.gross_annual_rent == 21_600
    assert numbers.effective_gross_rent == pytest.approx(20_304)
    # 1240 taxes + 700 insurance + 16% of gross rent
    assert numbers.annual_operating_expenses == pytest.approx(5_396)
    assert numbers.net_operating_income == pytest.approx(14_908)
    assert numbers.monthly_cash_flow == pytest.approx(231.02, abs=0.01)
    assert numbers.cap_rate == pytest.approx(0.071, abs=1e-4)
    assert numbers.cash_on_cash == pytest.approx(0.0495, abs=1e-4)
    assert numbers.dscr == pytest.approx(1.2284, abs=1e-4)
    assert numbers.max_allowable_offer == 165_000
    assert numbers.equity_capture == 40_000


def test_percentages_accept_either_form(inputs):
    whole = underwrite(inputs, Assumptions(down_payment_pct=20, interest_rate=6.5))
    fraction = underwrite(inputs, Assumptions(down_payment_pct=0.20, interest_rate=0.065))
    assert whole.monthly_payment == pytest.approx(fraction.monthly_payment)


def test_all_cash_purchase_has_no_debt_service(inputs):
    numbers = underwrite(inputs, Assumptions(down_payment_pct=1.0))
    assert numbers.loan_amount == 0
    assert numbers.annual_debt_service == 0
    assert math.isinf(numbers.dscr)
    # With no mortgage, all of the net operating income is cash flow.
    assert numbers.monthly_cash_flow == pytest.approx(14_908 / 12, abs=0.01)


def test_zero_rent_does_not_divide_by_zero(inputs, assumptions):
    numbers = underwrite(replace(inputs, monthly_rent=0.0), assumptions)
    assert numbers.gross_yield == 0.0
    assert math.isinf(numbers.price_to_rent)


def test_rehab_raises_cost_basis_and_cash_needed(inputs, assumptions):
    without = underwrite(replace(inputs, rehab_cost=0.0), assumptions)
    with_rehab = underwrite(inputs, assumptions)
    assert with_rehab.total_cost_basis - without.total_cost_basis == 10_000
    assert with_rehab.cash_to_close - without.cash_to_close == 10_000
    assert with_rehab.cap_rate < without.cap_rate


def test_breakeven_price_produces_zero_cash_flow(inputs, assumptions):
    price = breakeven_price(inputs, assumptions)
    at_breakeven = underwrite(replace(inputs, price=price), assumptions)
    assert at_breakeven.monthly_cash_flow == pytest.approx(0, abs=5)


def test_breakeven_price_scales_estimated_carrying_costs(assumptions):
    """When taxes come from the price, the search has to re-derive them."""
    estimated = DealInputs(
        price=400_000,
        monthly_rent=1_800,
        market_value=400_000,
        rehab_cost=0,
        annual_taxes=400_000 * 0.0062,
        annual_insurance=400_000 * 0.0035,
        monthly_hoa=0,
        provenance={"carrying_costs": "estimated:az-average"},
    )
    price = breakeven_price(estimated, assumptions)
    rescaled = replace(
        estimated,
        price=price,
        annual_taxes=price * 0.0062,
        annual_insurance=price * 0.0035,
    )
    assert underwrite(rescaled, assumptions).monthly_cash_flow == pytest.approx(0, abs=5)


def test_breakeven_is_zero_when_rent_cannot_cover_anything(inputs, assumptions):
    hopeless = replace(inputs, monthly_rent=1.0, annual_taxes=90_000, annual_insurance=0)
    assert breakeven_price(hopeless, assumptions) == 0.0
