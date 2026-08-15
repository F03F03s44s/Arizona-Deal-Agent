"""Score curves, pillars, budget rules, and ranking order."""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from arizona_deal_agent.finance import underwrite
from arizona_deal_agent.models import Assumptions, Budget, Listing, Weights
from arizona_deal_agent.scoring import (
    CAP_RATE_ANCHORS,
    check_budget,
    curve,
    discount_score,
    profitability_score,
    rank,
    score_listing,
)


def test_curve_hits_its_anchors_exactly():
    for value, expected in CAP_RATE_ANCHORS:
        assert curve(value, CAP_RATE_ANCHORS) == pytest.approx(expected)


def test_curve_interpolates_between_anchors():
    # Halfway between the 5% -> 50 and 7% -> 70 anchors.
    assert curve(0.06, CAP_RATE_ANCHORS) == pytest.approx(60.0)


def test_curve_clamps_outside_the_anchor_range():
    assert curve(-1.0, CAP_RATE_ANCHORS) == 0.0
    assert curve(99.0, CAP_RATE_ANCHORS) == 100.0


def test_curve_treats_infinite_dscr_as_the_top_of_the_range():
    assert curve(math.inf, CAP_RATE_ANCHORS) == 100.0


def test_discount_rewards_buying_under_market(inputs, assumptions):
    cheap = underwrite(replace(inputs, price=150_000), assumptions)
    dear = underwrite(replace(inputs, price=260_000), assumptions)

    assert discount_score(replace(inputs, price=150_000), cheap) > 80
    assert discount_score(replace(inputs, price=260_000), dear) < 30


def test_all_cash_is_not_punished_for_having_no_debt(inputs):
    """Infinite DSCR is perfect coverage, not a missing value."""
    financed = underwrite(inputs, Assumptions(down_payment_pct=0.20))
    all_cash = underwrite(inputs, Assumptions(down_payment_pct=1.0))

    assert profitability_score(all_cash) > profitability_score(financed)


def test_scores_do_not_depend_on_the_rest_of_the_batch(listing, market, assumptions):
    """Anchored scoring means one deal scores the same alone or in a crowd."""
    from arizona_deal_agent.enrich import enrich

    only = score_listing(listing, enrich(listing, market).inputs, assumptions)
    others = [
        score_listing(
            replace(listing, id=f"other-{n}", list_price=100_000 * n),
            enrich(replace(listing, list_price=100_000 * n), market).inputs,
            assumptions,
        )
        for n in range(1, 6)
    ]
    again = score_listing(listing, enrich(listing, market).inputs, assumptions)

    assert only.score.composite == again.score.composite
    assert all(isinstance(deal.score.composite, float) for deal in others)


def test_weights_change_the_ranking(market, assumptions):
    from arizona_deal_agent.enrich import enrich

    # A steep discount but weak returns, against a full-price strong earner.
    bargain = Listing(id="bargain", source="t", zip_code="85041", list_price=250_000, monthly_rent=1_300)
    earner = Listing(id="earner", source="t", zip_code="85041", list_price=360_000, monthly_rent=3_400)

    def composite(listing, weights):
        return score_listing(listing, enrich(listing, market).inputs, assumptions, Budget(), weights).score.composite

    discount_first = Weights(discount=1, profitability=0, affordability=0)
    profit_first = Weights(discount=0, profitability=1, affordability=0)

    assert composite(bargain, discount_first) > composite(earner, discount_first)
    assert composite(earner, profit_first) > composite(bargain, profit_first)


def test_weights_are_normalised():
    doubled = Weights(discount=0.5, profitability=0.8, affordability=0.7).normalised()
    assert doubled.discount + doubled.profitability + doubled.affordability == pytest.approx(1.0)


def test_zero_weights_fall_back_to_the_defaults():
    assert Weights(0, 0, 0).normalised() == Weights()


def test_budget_misses_are_reported_individually(inputs, assumptions):
    numbers = underwrite(inputs, assumptions)
    misses = check_budget(
        inputs,
        numbers,
        Budget(max_price=150_000, max_cash_to_close=20_000, min_cash_flow=500, min_cap_rate=0.09),
    )
    assert len(misses) == 4
    assert any("price" in m for m in misses)
    assert any("closing" in m for m in misses)
    assert any("cash flow" in m for m in misses)
    assert any("cap rate" in m for m in misses)


def test_a_deal_inside_the_budget_reports_no_misses(inputs, assumptions):
    numbers = underwrite(inputs, assumptions)
    assert check_budget(inputs, numbers, Budget(max_price=250_000, min_cash_flow=0)) == []


def test_affordability_uses_rent_coverage_when_no_budget_is_set(inputs, assumptions, listing):
    deal = score_listing(listing, inputs, assumptions, Budget())
    assert 0 <= deal.score.affordability <= 100


def test_affordability_falls_as_the_deal_eats_more_of_the_budget(listing, inputs, assumptions):
    roomy = score_listing(listing, inputs, assumptions, Budget(max_cash_to_close=200_000))
    tight = score_listing(listing, inputs, assumptions, Budget(max_cash_to_close=60_000))
    assert roomy.score.affordability > tight.score.affordability


def test_rank_puts_the_best_score_first_and_budget_misses_last(listing, inputs, assumptions):
    good = score_listing(replace(listing, id="good"), replace(inputs, price=150_000), assumptions)
    poor = score_listing(replace(listing, id="poor"), replace(inputs, price=249_000), assumptions)
    blocked = score_listing(
        replace(listing, id="blocked"),
        replace(inputs, price=140_000),
        assumptions,
        Budget(max_price=100_000),
    )

    order = [deal.listing.id for deal in rank([poor, blocked, good])]
    assert order == ["good", "poor", "blocked"]


def test_estimated_inputs_produce_warnings(market, assumptions):
    from arizona_deal_agent.enrich import enrich

    bare = Listing(id="HUD-1", source="hud-reo", zip_code="85041")
    deal = score_listing(bare, enrich(bare, market).inputs, assumptions)

    assert any("Price is an estimate" in w for w in deal.warnings)
    assert any("Rent is an estimate" in w for w in deal.warnings)


def test_listed_inputs_produce_no_warnings(listing, inputs, assumptions):
    assert score_listing(listing, inputs, assumptions).warnings == []


def test_reasons_mention_the_breakeven_price_when_cash_flow_is_negative(listing, inputs, assumptions):
    underwater = replace(inputs, price=500_000, monthly_rent=900)
    deal = score_listing(listing, underwater, assumptions)

    assert deal.underwriting.monthly_cash_flow < 0
    assert any("Breaks even" in reason for reason in deal.reasons)
    assert deal.breakeven_price < underwater.price
