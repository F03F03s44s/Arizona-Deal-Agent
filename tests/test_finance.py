"""The finance math is the part that must be right, so it is checked by hand."""

from dataclasses import replace

import pytest

from arizona_deal_agent import finance
from arizona_deal_agent.models import Assumptions, Listing


class TestMortgagePayment:
    def test_matches_published_amortization_value(self):
        # $300k at 6.5% over 30 years is $1,896.20/mo in any amortization table.
        assert finance.monthly_mortgage_payment(300_000, 0.065, 30) == pytest.approx(1896.20, abs=0.01)

    def test_zero_rate_pays_principal_in_equal_slices(self):
        assert finance.monthly_mortgage_payment(120_000, 0.0, 10) == pytest.approx(1000.0)

    def test_no_principal_means_no_payment(self):
        assert finance.monthly_mortgage_payment(0, 0.065, 30) == 0.0
        assert finance.monthly_mortgage_payment(-5_000, 0.065, 30) == 0.0

    def test_payment_scales_linearly_with_principal(self):
        full = finance.monthly_mortgage_payment(300_000, 0.065, 30)
        eighty_percent = finance.monthly_mortgage_payment(240_000, 0.065, 30)
        assert eighty_percent == pytest.approx(full * 0.8)

    def test_higher_rate_costs_more(self):
        cheap = finance.monthly_mortgage_payment(300_000, 0.05, 30)
        dear = finance.monthly_mortgage_payment(300_000, 0.08, 30)
        assert dear > cheap

    def test_longer_term_lowers_the_payment(self):
        assert finance.monthly_mortgage_payment(300_000, 0.065, 30) < finance.monthly_mortgage_payment(
            300_000, 0.065, 15
        )


class TestIncomeAndExpenses:
    def test_gross_and_effective_rent(self, listing, assumptions):
        assert finance.gross_annual_rent(listing) == 24_000
        # 6% vacancy on $24,000.
        assert finance.effective_gross_rent(listing, assumptions) == pytest.approx(22_560)

    def test_operating_expenses_sum_fixed_and_variable(self, listing, assumptions):
        # taxes 2,400 + insurance 1,200 + HOA 1,200 + 16% of $24,000 gross rent.
        assert finance.annual_operating_expenses(listing, assumptions) == pytest.approx(8_640)

    def test_net_operating_income(self, listing, assumptions):
        assert finance.net_operating_income(listing, assumptions) == pytest.approx(13_920)

    def test_noi_ignores_financing(self, listing, assumptions):
        expensive_debt = replace(assumptions, interest_rate=0.12, down_payment_pct=0.05)
        assert finance.net_operating_income(listing, expensive_debt) == pytest.approx(
            finance.net_operating_income(listing, assumptions)
        )


class TestPurchaseCosts:
    def test_cash_to_close_adds_down_payment_closing_and_rehab(self, listing, assumptions):
        # 20% of 300,000 + 3% of 300,000 + 0 rehab.
        assert finance.cash_to_close(listing, assumptions) == pytest.approx(69_000)

    def test_rehab_is_part_of_cash_to_close_and_basis(self, listing, assumptions):
        with_rehab = replace(listing, rehab_cost=20_000)
        assert finance.cash_to_close(with_rehab, assumptions) == pytest.approx(89_000)
        assert finance.total_cost_basis(with_rehab) == 320_000

    def test_loan_amount_is_price_less_down_payment(self, listing, assumptions):
        assert finance.loan_amount(listing, assumptions) == pytest.approx(240_000)


class TestReturns:
    def test_cap_rate_divides_noi_by_basis(self, listing, assumptions):
        assert finance.cap_rate(listing, assumptions) == pytest.approx(13_920 / 300_000)

    def test_rehab_dilutes_cap_rate(self, listing, assumptions):
        with_rehab = replace(listing, rehab_cost=50_000)
        assert finance.cap_rate(with_rehab, assumptions) < finance.cap_rate(listing, assumptions)

    def test_cash_on_cash_uses_cash_invested(self, listing, assumptions):
        expected = finance.annual_cash_flow(listing, assumptions) / 69_000
        assert finance.cash_on_cash_return(listing, assumptions) == pytest.approx(expected)

    def test_this_listing_does_not_cover_its_debt(self, listing, assumptions):
        # NOI 13,920 against roughly 18,200 of debt service.
        assert finance.annual_cash_flow(listing, assumptions) < 0
        assert finance.debt_service_coverage_ratio(listing, assumptions) < 1.0

    def test_all_cash_purchase_reports_no_debt_coverage(self, listing, assumptions):
        all_cash = replace(assumptions, down_payment_pct=1.0)
        assert finance.annual_debt_service(listing, all_cash) == 0.0
        assert finance.debt_service_coverage_ratio(listing, all_cash) == 0.0
        assert finance.annual_cash_flow(listing, all_cash) == pytest.approx(13_920)

    def test_cash_on_cash_is_zero_without_investment(self, listing):
        free_money = Assumptions(down_payment_pct=0.0, closing_cost_pct=0.0)
        assert finance.cash_to_close(listing, free_money) == 0
        assert finance.cash_on_cash_return(listing, free_money) == 0.0


class TestAffordabilityInputs:
    def test_carrying_cost_is_mortgage_plus_taxes_insurance_hoa(self, listing, assumptions):
        mortgage = finance.monthly_mortgage_payment(240_000, 0.065, 30)
        assert finance.monthly_carrying_cost(listing, assumptions) == pytest.approx(mortgage + 300 + 100)

    def test_price_to_rent(self, listing):
        assert finance.price_to_rent_ratio(listing) == pytest.approx(12.5)

    def test_price_to_rent_undefined_without_rent(self, listing):
        assert finance.price_to_rent_ratio(replace(listing, monthly_rent=0)) is None

    def test_rent_coverage_compares_rent_to_carrying_cost(self, listing, assumptions):
        carrying = finance.monthly_carrying_cost(listing, assumptions)
        assert finance.rent_coverage(listing, assumptions) == pytest.approx(2_000 / carrying)

    def test_rent_coverage_undefined_when_nothing_is_owed(self):
        free_and_clear = Listing(id="X", address="a", city="b", list_price=100_000, monthly_rent=1_000)
        no_debt = Assumptions(down_payment_pct=1.0)
        assert finance.rent_coverage(free_and_clear, no_debt) is None


class TestFlipMath:
    def test_seventy_percent_rule(self, listing, assumptions):
        flip = replace(listing, list_price=189_000, rehab_cost=42_000, arv=340_000)
        # 340,000 * 0.70 - 42,000
        assert finance.max_allowable_offer(flip, assumptions) == pytest.approx(196_000)
        assert finance.equity_capture(flip, assumptions) == pytest.approx(7_000)

    def test_overpriced_flip_has_negative_equity(self, listing, assumptions):
        flip = replace(listing, list_price=260_000, rehab_cost=42_000, arv=340_000)
        assert finance.equity_capture(flip, assumptions) == pytest.approx(-64_000)

    def test_no_arv_means_no_flip_metrics(self, listing, assumptions):
        assert finance.max_allowable_offer(listing, assumptions) is None
        assert finance.equity_capture(listing, assumptions) is None

    def test_flip_rule_is_configurable(self, listing):
        flip = replace(listing, list_price=189_000, rehab_cost=42_000, arv=340_000)
        strict = Assumptions(flip_rule_pct=0.65)
        assert finance.max_allowable_offer(flip, strict) == pytest.approx(340_000 * 0.65 - 42_000)


class TestComputeMetrics:
    def test_bundle_matches_individual_functions(self, listing, assumptions):
        metrics = finance.compute_metrics(listing, assumptions)
        assert metrics.net_operating_income == pytest.approx(finance.net_operating_income(listing, assumptions))
        assert metrics.cap_rate == pytest.approx(finance.cap_rate(listing, assumptions))
        assert metrics.cash_on_cash == pytest.approx(finance.cash_on_cash_return(listing, assumptions))
        assert metrics.dscr == pytest.approx(finance.debt_service_coverage_ratio(listing, assumptions))
        assert metrics.cash_to_close == pytest.approx(finance.cash_to_close(listing, assumptions))
        assert metrics.monthly_carrying_cost == pytest.approx(
            finance.monthly_carrying_cost(listing, assumptions)
        )

    def test_monthly_and_annual_cash_flow_agree(self, listing, assumptions):
        metrics = finance.compute_metrics(listing, assumptions)
        assert metrics.monthly_cash_flow * 12 == pytest.approx(metrics.annual_cash_flow)
