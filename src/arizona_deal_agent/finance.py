"""Property investment math.

Every function here is pure: same inputs, same outputs, no I/O. The formulas are
the standard buy-and-hold and fix-and-flip calculations a real estate investor
would run by hand, so they can be checked against any rental calculator.
"""

from __future__ import annotations

from .models import Assumptions, Listing, Metrics

MONTHS_PER_YEAR = 12


def monthly_mortgage_payment(principal: float, annual_rate: float, term_years: int) -> float:
    """Fully amortizing payment: ``P * r(1+r)^n / ((1+r)^n - 1)``.

    A zero interest rate makes that formula divide by zero, so it degrades to a
    straight-line payoff.
    """
    if principal <= 0:
        return 0.0
    periods = term_years * MONTHS_PER_YEAR
    monthly_rate = annual_rate / MONTHS_PER_YEAR
    if monthly_rate == 0:
        return principal / periods
    growth = (1 + monthly_rate) ** periods
    return principal * monthly_rate * growth / (growth - 1)


def loan_amount(listing: Listing, assumptions: Assumptions) -> float:
    return listing.list_price * (1 - assumptions.down_payment_pct)


def cash_to_close(listing: Listing, assumptions: Assumptions) -> float:
    """Down payment plus closing costs plus rehab -- the money actually needed."""
    down_payment = listing.list_price * assumptions.down_payment_pct
    closing_costs = listing.list_price * assumptions.closing_cost_pct
    return down_payment + closing_costs + listing.rehab_cost


def total_cost_basis(listing: Listing) -> float:
    return listing.list_price + listing.rehab_cost


def gross_annual_rent(listing: Listing) -> float:
    return listing.monthly_rent * MONTHS_PER_YEAR


def effective_gross_rent(listing: Listing, assumptions: Assumptions) -> float:
    """Gross rent less expected vacancy."""
    return gross_annual_rent(listing) * (1 - assumptions.vacancy_rate)


def annual_operating_expenses(listing: Listing, assumptions: Assumptions) -> float:
    """Taxes, insurance, HOA and reserves.

    Maintenance and management are quoted as a share of *gross* rent, which is
    how property managers price them.
    """
    gross_rent = gross_annual_rent(listing)
    variable = gross_rent * (assumptions.maintenance_rate + assumptions.management_rate)
    fixed = listing.annual_taxes + listing.annual_insurance + listing.monthly_hoa * MONTHS_PER_YEAR
    return fixed + variable


def net_operating_income(listing: Listing, assumptions: Assumptions) -> float:
    """NOI -- income after operating costs but before financing."""
    return effective_gross_rent(listing, assumptions) - annual_operating_expenses(listing, assumptions)


def cap_rate(listing: Listing, assumptions: Assumptions) -> float:
    """NOI divided by everything paid to own the asset, rehab included."""
    basis = total_cost_basis(listing)
    if basis <= 0:
        return 0.0
    return net_operating_income(listing, assumptions) / basis


def annual_debt_service(listing: Listing, assumptions: Assumptions) -> float:
    payment = monthly_mortgage_payment(
        loan_amount(listing, assumptions), assumptions.interest_rate, assumptions.loan_term_years
    )
    return payment * MONTHS_PER_YEAR


def annual_cash_flow(listing: Listing, assumptions: Assumptions) -> float:
    return net_operating_income(listing, assumptions) - annual_debt_service(listing, assumptions)


def cash_on_cash_return(listing: Listing, assumptions: Assumptions) -> float:
    """Annual cash flow divided by the cash actually invested."""
    invested = cash_to_close(listing, assumptions)
    if invested <= 0:
        return 0.0
    return annual_cash_flow(listing, assumptions) / invested


def debt_service_coverage_ratio(listing: Listing, assumptions: Assumptions) -> float:
    """DSCR -- lenders generally want 1.20 or better.

    An all-cash purchase has no debt to cover, reported here as 0.0 rather than
    infinity so the value stays sortable.
    """
    debt = annual_debt_service(listing, assumptions)
    if debt <= 0:
        return 0.0
    return net_operating_income(listing, assumptions) / debt


def monthly_carrying_cost(listing: Listing, assumptions: Assumptions) -> float:
    """What leaves the owner's account each month: PITI plus HOA."""
    mortgage = monthly_mortgage_payment(
        loan_amount(listing, assumptions), assumptions.interest_rate, assumptions.loan_term_years
    )
    taxes_and_insurance = (listing.annual_taxes + listing.annual_insurance) / MONTHS_PER_YEAR
    return mortgage + taxes_and_insurance + listing.monthly_hoa


def price_to_rent_ratio(listing: Listing) -> float | None:
    """List price divided by one year of rent. Lower is cheaper."""
    annual_rent = gross_annual_rent(listing)
    if annual_rent <= 0:
        return None
    return listing.list_price / annual_rent


def rent_coverage(listing: Listing, assumptions: Assumptions) -> float | None:
    """How far the rent goes toward the monthly carrying cost. 1.0 breaks even."""
    carrying = monthly_carrying_cost(listing, assumptions)
    if carrying <= 0:
        return None
    return listing.monthly_rent / carrying


def max_allowable_offer(listing: Listing, assumptions: Assumptions) -> float | None:
    """The 70% rule: ``ARV * 0.70 - rehab``. Needs an ARV estimate."""
    if listing.arv is None:
        return None
    return listing.arv * assumptions.flip_rule_pct - listing.rehab_cost


def equity_capture(listing: Listing, assumptions: Assumptions) -> float | None:
    """Dollars below the max allowable offer. Positive means room to profit."""
    mao = max_allowable_offer(listing, assumptions)
    if mao is None:
        return None
    return mao - listing.list_price


def compute_metrics(listing: Listing, assumptions: Assumptions) -> Metrics:
    """Run every calculation above once and return them together."""
    return Metrics(
        total_cost_basis=total_cost_basis(listing),
        cash_to_close=cash_to_close(listing, assumptions),
        loan_amount=loan_amount(listing, assumptions),
        monthly_mortgage=monthly_mortgage_payment(
            loan_amount(listing, assumptions), assumptions.interest_rate, assumptions.loan_term_years
        ),
        monthly_carrying_cost=monthly_carrying_cost(listing, assumptions),
        monthly_cash_flow=annual_cash_flow(listing, assumptions) / MONTHS_PER_YEAR,
        effective_gross_rent=effective_gross_rent(listing, assumptions),
        annual_operating_expenses=annual_operating_expenses(listing, assumptions),
        net_operating_income=net_operating_income(listing, assumptions),
        annual_debt_service=annual_debt_service(listing, assumptions),
        annual_cash_flow=annual_cash_flow(listing, assumptions),
        cap_rate=cap_rate(listing, assumptions),
        cash_on_cash=cash_on_cash_return(listing, assumptions),
        dscr=debt_service_coverage_ratio(listing, assumptions),
        price_to_rent=price_to_rent_ratio(listing),
        rent_coverage=rent_coverage(listing, assumptions),
        max_allowable_offer=max_allowable_offer(listing, assumptions),
        equity_capture=equity_capture(listing, assumptions),
    )
