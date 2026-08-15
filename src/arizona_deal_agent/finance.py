"""Rental-property underwriting math.

Everything here is a pure function of the deal inputs and the assumptions, so
the same listing always produces the same numbers.
"""

from __future__ import annotations

import math

from .models import Assumptions, DealInputs, Underwriting


def monthly_payment(principal: float, annual_rate: float, term_years: int) -> float:
    """Level-payment amortised mortgage payment."""
    if principal <= 0:
        return 0.0
    months = max(1, int(round(term_years * 12)))
    if annual_rate <= 0:
        return principal / months
    monthly_rate = annual_rate / 12.0
    growth = (1.0 + monthly_rate) ** months
    return principal * monthly_rate * growth / (growth - 1.0)


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return math.inf if numerator > 0 else 0.0
    return numerator / denominator


def underwrite(inputs: DealInputs, assumptions: Assumptions) -> Underwriting:
    """Run one deal through the finance model."""
    a = assumptions.normalised()

    price = max(0.0, inputs.price)
    rehab = max(0.0, inputs.rehab_cost)
    total_cost_basis = price + rehab

    down_payment = price * a.down_payment_pct
    loan_amount = max(0.0, price - down_payment)
    closing_costs = price * a.closing_cost_pct
    cash_to_close = down_payment + closing_costs + rehab

    payment = monthly_payment(loan_amount, a.interest_rate, a.term_years)
    monthly_taxes_insurance = (inputs.annual_taxes + inputs.annual_insurance) / 12.0
    monthly_carrying_cost = payment + monthly_taxes_insurance + inputs.monthly_hoa

    gross_annual_rent = inputs.monthly_rent * 12.0
    effective_gross_rent = gross_annual_rent * (1.0 - a.vacancy_pct)
    variable_expenses = gross_annual_rent * (a.maintenance_pct + a.management_pct)
    annual_operating_expenses = (
        inputs.annual_taxes
        + inputs.annual_insurance
        + inputs.monthly_hoa * 12.0
        + variable_expenses
    )
    net_operating_income = effective_gross_rent - annual_operating_expenses

    annual_debt_service = payment * 12.0
    annual_cash_flow = net_operating_income - annual_debt_service

    # An all-cash purchase carries no debt, so it trivially covers its (zero)
    # debt service. Reporting infinite DSCR keeps it from being scored as if it
    # had failed a coverage test.
    dscr = math.inf if annual_debt_service == 0 else net_operating_income / annual_debt_service

    max_allowable_offer = max(0.0, a.flip_rule * inputs.market_value - rehab)

    return Underwriting(
        total_cost_basis=total_cost_basis,
        down_payment=down_payment,
        loan_amount=loan_amount,
        closing_costs=closing_costs,
        cash_to_close=cash_to_close,
        monthly_payment=payment,
        monthly_taxes_insurance=monthly_taxes_insurance,
        monthly_hoa=inputs.monthly_hoa,
        monthly_carrying_cost=monthly_carrying_cost,
        monthly_cash_flow=annual_cash_flow / 12.0,
        gross_annual_rent=gross_annual_rent,
        effective_gross_rent=effective_gross_rent,
        annual_operating_expenses=annual_operating_expenses,
        net_operating_income=net_operating_income,
        annual_debt_service=annual_debt_service,
        annual_cash_flow=annual_cash_flow,
        cap_rate=_safe_div(net_operating_income, total_cost_basis),
        cash_on_cash=_safe_div(annual_cash_flow, cash_to_close),
        dscr=dscr,
        gross_yield=_safe_div(gross_annual_rent, total_cost_basis),
        price_to_rent=_safe_div(price, gross_annual_rent),
        max_allowable_offer=max_allowable_offer,
        equity_capture=inputs.market_value - total_cost_basis,
    )


def breakeven_price(
    inputs: DealInputs,
    assumptions: Assumptions,
    target_cash_flow: float = 0.0,
    tolerance: float = 1.0,
) -> float:
    """Highest purchase price that still clears ``target_cash_flow`` per month.

    Taxes and insurance scale with price, so cash flow is not a closed form.
    A bisection search is used instead; cash flow falls monotonically as price
    rises, which makes the search well behaved.
    """
    from dataclasses import replace

    scales_with_price = inputs.provenance.get("carrying_costs") == "estimated:az-average"

    def cash_flow_at(price: float) -> float:
        candidate = replace(inputs, price=price)
        if scales_with_price:
            from .models import AZ_INSURANCE_RATE, AZ_TAX_RATE

            candidate = replace(
                candidate,
                annual_taxes=price * AZ_TAX_RATE,
                annual_insurance=price * AZ_INSURANCE_RATE,
            )
        return underwrite(candidate, assumptions).monthly_cash_flow

    low, high = 0.0, max(inputs.price, inputs.market_value, 1.0) * 3.0
    if cash_flow_at(low) < target_cash_flow:
        return 0.0
    if cash_flow_at(high) >= target_cash_flow:
        return high

    while high - low > tolerance:
        mid = (low + high) / 2.0
        if cash_flow_at(mid) >= target_cash_flow:
            low = mid
        else:
            high = mid
    return low
