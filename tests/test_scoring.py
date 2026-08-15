"""Scores must be bounded, stable, and move in the direction a buyer expects."""

from dataclasses import replace

import pytest

from arizona_deal_agent import finance, scoring
from arizona_deal_agent.models import Assumptions, Budget, Listing, ValidationError, Weights


class TestInterpolate:
    curve = ((0.0, 0.0), (10.0, 50.0), (20.0, 100.0))

    def test_hits_the_anchor_points(self):
        assert scoring.interpolate(0.0, self.curve) == 0.0
        assert scoring.interpolate(10.0, self.curve) == 50.0
        assert scoring.interpolate(20.0, self.curve) == 100.0

    def test_interpolates_between_anchors(self):
        assert scoring.interpolate(5.0, self.curve) == pytest.approx(25.0)
        assert scoring.interpolate(15.0, self.curve) == pytest.approx(75.0)

    def test_clamps_outside_the_range(self):
        assert scoring.interpolate(-100.0, self.curve) == 0.0
        assert scoring.interpolate(1_000.0, self.curve) == 100.0

    def test_handles_descending_scores(self):
        descending = ((9.0, 100.0), (20.0, 0.0))
        assert scoring.interpolate(9.0, descending) == 100.0
        assert scoring.interpolate(20.0, descending) == 0.0
        assert scoring.interpolate(14.5, descending) == pytest.approx(50.0)

    def test_single_anchor_is_constant(self):
        assert scoring.interpolate(-5.0, ((1.0, 42.0),)) == 42.0
        assert scoring.interpolate(500.0, ((1.0, 42.0),)) == 42.0

    def test_empty_curve_is_rejected(self):
        with pytest.raises(ValueError):
            scoring.interpolate(1.0, ())


def rental(price: float, rent: float, **overrides) -> Listing:
    defaults = dict(
        id=overrides.pop("id", "L"),
        address="1 Test Way",
        city="Phoenix",
        list_price=price,
        monthly_rent=rent,
        annual_taxes=price * 0.0062,
        annual_insurance=price * 0.0035,
    )
    defaults.update(overrides)
    return Listing(**defaults)


class TestComponentScores:
    def test_more_rent_scores_more_profitable(self, assumptions):
        weak = finance.compute_metrics(rental(350_000, 1_800), assumptions)
        strong = finance.compute_metrics(rental(350_000, 3_200), assumptions)
        assert scoring.profitability_score(strong) > scoring.profitability_score(weak)

    def test_lower_price_scores_cheaper(self, assumptions):
        cheap = rental(250_000, 2_000)
        dear = rental(450_000, 2_000)
        cheap_score = scoring.price_score(cheap, finance.compute_metrics(cheap, assumptions))
        dear_score = scoring.price_score(dear, finance.compute_metrics(dear, assumptions))
        assert cheap_score > dear_score

    def test_scores_stay_within_bounds(self, assumptions):
        extremes = [rental(60_000, 4_000), rental(2_000_000, 500), rental(300_000, 2_000)]
        for listing in extremes:
            metrics = finance.compute_metrics(listing, assumptions)
            for score in (
                scoring.price_score(listing, metrics),
                scoring.profitability_score(metrics),
                scoring.affordability_score(listing, metrics, Budget()),
            ):
                assert 0.0 <= score <= 100.0

    def test_an_arv_can_only_help_the_price_score(self, assumptions):
        base = rental(189_000, 1_450, rehab_cost=42_000)
        with_arv = replace(base, arv=340_000)
        without = scoring.price_score(base, finance.compute_metrics(base, assumptions))
        with_flip = scoring.price_score(with_arv, finance.compute_metrics(with_arv, assumptions))
        assert with_flip >= without

    def test_all_cash_is_not_punished_for_having_no_debt_coverage(self, assumptions):
        listing = rental(300_000, 2_000)
        all_cash = replace(assumptions, down_payment_pct=1.0)
        leveraged = finance.compute_metrics(listing, assumptions)
        unleveraged = finance.compute_metrics(listing, all_cash)
        # DSCR is reported as 0.0 when there is no debt; that must not read as failure.
        assert unleveraged.dscr == 0.0
        assert scoring.profitability_score(unleveraged) > scoring.profitability_score(leveraged)

    def test_a_property_with_nothing_to_pay_is_fully_affordable(self):
        free_to_hold = Listing(id="F", list_price=100_000, monthly_rent=1_000)
        no_debt = Assumptions(down_payment_pct=1.0)
        metrics = finance.compute_metrics(free_to_hold, no_debt)
        assert metrics.rent_coverage is None
        assert scoring.affordability_score(free_to_hold, metrics, Budget()) == 100.0

    def test_deep_discount_lifts_the_price_score(self, assumptions):
        thin = rental(300_000, 1_400, rehab_cost=20_000, arv=340_000)
        deep = rental(150_000, 1_400, rehab_cost=20_000, arv=340_000)
        thin_score = scoring.price_score(thin, finance.compute_metrics(thin, assumptions))
        deep_score = scoring.price_score(deep, finance.compute_metrics(deep, assumptions))
        assert deep_score > thin_score


class TestAffordability:
    def test_without_a_budget_it_measures_rent_coverage(self, assumptions):
        covered = rental(250_000, 2_600)
        stretched = rental(600_000, 2_600)
        covered_score = scoring.affordability_score(
            covered, finance.compute_metrics(covered, assumptions), Budget()
        )
        stretched_score = scoring.affordability_score(
            stretched, finance.compute_metrics(stretched, assumptions), Budget()
        )
        assert covered_score > stretched_score

    def test_a_budget_rewards_headroom(self, assumptions):
        listing = rental(300_000, 2_000)
        metrics = finance.compute_metrics(listing, assumptions)
        roomy = scoring.affordability_score(listing, metrics, Budget(max_price=600_000))
        tight = scoring.affordability_score(listing, metrics, Budget(max_price=300_000))
        over = scoring.affordability_score(listing, metrics, Budget(max_price=210_000))
        assert roomy > tight > over

    def test_the_tightest_limit_decides(self, assumptions):
        listing = rental(300_000, 2_000)
        metrics = finance.compute_metrics(listing, assumptions)
        price_only = scoring.affordability_score(listing, metrics, Budget(max_price=600_000))
        plus_cash_squeeze = scoring.affordability_score(
            listing, metrics, Budget(max_price=600_000, max_cash_to_close=40_000)
        )
        assert plus_cash_squeeze < price_only


class TestFitsBudget:
    def test_empty_budget_accepts_everything(self, assumptions):
        listing = rental(900_000, 1_000)
        metrics = finance.compute_metrics(listing, assumptions)
        assert scoring.fits_budget(listing, metrics, Budget()) is True

    @pytest.mark.parametrize(
        "budget,expected",
        [
            (Budget(max_price=250_000), False),
            (Budget(max_price=400_000), True),
            (Budget(max_cash_to_close=10_000), False),
            (Budget(max_cash_to_close=200_000), True),
            (Budget(max_monthly_payment=500), False),
            (Budget(max_monthly_payment=10_000), True),
        ],
    )
    def test_each_limit_is_enforced(self, assumptions, budget, expected):
        listing = rental(300_000, 2_000)
        metrics = finance.compute_metrics(listing, assumptions)
        assert scoring.fits_budget(listing, metrics, budget) is expected


class TestScoreListing:
    def test_composite_is_the_weighted_average_of_components(self, assumptions):
        weights = Weights(price=0.25, profitability=0.40, affordability=0.35)
        deal = scoring.score_listing(rental(300_000, 2_000), assumptions, Budget(), weights)
        expected = (
            deal.price_score * 0.25 + deal.profitability_score * 0.40 + deal.affordability_score * 0.35
        )
        assert deal.composite_score == pytest.approx(expected)

    def test_weights_are_normalized_not_taken_literally(self, assumptions):
        listing = rental(300_000, 2_000)
        unit = scoring.score_listing(listing, assumptions, Budget(), Weights(0.25, 0.40, 0.35))
        scaled = scoring.score_listing(listing, assumptions, Budget(), Weights(2.5, 4.0, 3.5))
        assert unit.composite_score == pytest.approx(scaled.composite_score)

    def test_weights_change_the_ordering(self, assumptions):
        # Priced well against its rent, but $700/mo of HOA dues eat the returns.
        bargain_with_dues = rental(150_000, 1_600, id="bargain", monthly_hoa=700)
        # Priced less keenly, yet it clears its costs comfortably.
        earner = rental(420_000, 3_500, id="earner")
        listings = [bargain_with_dues, earner]

        by_price = scoring.rank_listings(listings, assumptions, None, Weights(1, 0, 0))
        by_profit = scoring.rank_listings(listings, assumptions, None, Weights(0, 1, 0))
        assert by_price[0].listing.id == "bargain"
        assert by_profit[0].listing.id == "earner"

    def test_negative_weights_are_rejected(self):
        with pytest.raises(ValidationError):
            Weights(price=-1)

    def test_all_zero_weights_are_rejected(self):
        with pytest.raises(ValidationError):
            Weights(0, 0, 0)

    def test_defaults_are_used_when_nothing_is_passed(self):
        deal = scoring.score_listing(rental(300_000, 2_000))
        assert 0 <= deal.composite_score <= 100
        assert deal.qualifies is True

    def test_notes_flag_negative_cash_flow_without_a_double_sign(self, assumptions):
        deal = scoring.score_listing(rental(600_000, 1_200), assumptions)
        negative = [note for note in deal.notes if note.startswith("Negative cash flow")]
        assert negative and "$-" not in negative[0]


class TestRanking:
    def test_best_deal_comes_first(self, assumptions):
        listings = [rental(500_000, 1_500, id="bad"), rental(220_000, 2_400, id="good")]
        ranked = scoring.rank_listings(listings, assumptions)
        assert [deal.listing.id for deal in ranked] == ["good", "bad"]

    def test_scores_descend(self, assumptions, sample_csv):
        from arizona_deal_agent.sources import load_listings

        ranked = scoring.rank_listings(load_listings(sample_csv), assumptions)
        scores = [deal.composite_score for deal in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_ties_break_on_price_then_id(self, assumptions):
        twins = [rental(300_000, 2_000, id="b"), rental(300_000, 2_000, id="a")]
        ranked = scoring.rank_listings(twins, assumptions)
        assert [deal.listing.id for deal in ranked] == ["a", "b"]

    def test_a_listing_scores_the_same_alone_as_in_a_crowd(self, assumptions, sample_csv):
        from arizona_deal_agent.sources import load_listings

        listings = load_listings(sample_csv)
        in_crowd = {deal.listing.id: deal.composite_score for deal in scoring.rank_listings(listings, assumptions)}
        for listing in listings:
            alone = scoring.score_listing(listing, assumptions)
            assert alone.composite_score == pytest.approx(in_crowd[listing.id])

    def test_empty_input_gives_empty_output(self, assumptions):
        assert scoring.rank_listings([], assumptions) == []


class TestAssumptionValidation:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"down_payment_pct": 1.5},
            {"down_payment_pct": -0.1},
            {"interest_rate": -0.01},
            {"loan_term_years": 0},
            {"vacancy_rate": 0.5, "maintenance_rate": 0.3, "management_rate": 0.3},
        ],
    )
    def test_impossible_assumptions_are_rejected(self, kwargs):
        with pytest.raises(ValidationError):
            Assumptions(**kwargs)

    @pytest.mark.parametrize("kwargs", [{"list_price": 0}, {"list_price": -1}, {"monthly_rent": -5}, {"arv": 0}])
    def test_impossible_listings_are_rejected(self, kwargs):
        base = dict(id="X", address="a", city="b", list_price=100_000, monthly_rent=1_000)
        base.update(kwargs)
        with pytest.raises(ValidationError):
            Listing(**base)

    def test_budget_limits_must_be_positive(self):
        with pytest.raises(ValidationError):
            Budget(max_price=-1)
