"""Turn underwriting output into a 0-100 best-value score.

Scores are anchored to fixed benchmarks rather than to the rest of the batch, so
a property scores the same whether it is ranked alone or against a thousand
others, and two runs are comparable. A 7% cap rate is a 70 today and a 70 next
week.
"""

from __future__ import annotations

import math

from .enrich import LISTED, describe
from .finance import breakeven_price, underwrite
from .models import (
    Assumptions,
    Budget,
    DealInputs,
    Listing,
    ScoredDeal,
    Underwriting,
    ValueScore,
    Weights,
)

Anchors = tuple[tuple[float, float], ...]

# (metric value, score) pairs, ascending. Between anchors the score is
# interpolated linearly; outside them it is clamped.
DISCOUNT_ANCHORS: Anchors = ((-0.25, 0.0), (-0.10, 20.0), (0.0, 50.0), (0.10, 72.0), (0.20, 88.0), (0.35, 100.0))
CAP_RATE_ANCHORS: Anchors = ((0.0, 0.0), (0.03, 25.0), (0.05, 50.0), (0.07, 70.0), (0.09, 88.0), (0.12, 100.0))
CASH_ON_CASH_ANCHORS: Anchors = ((-0.05, 0.0), (0.0, 30.0), (0.04, 55.0), (0.08, 75.0), (0.12, 90.0), (0.18, 100.0))
DSCR_ANCHORS: Anchors = ((0.8, 0.0), (1.0, 40.0), (1.2, 70.0), (1.35, 85.0), (1.6, 100.0))
CASH_FLOW_ANCHORS: Anchors = ((-400.0, 0.0), (-100.0, 25.0), (0.0, 45.0), (150.0, 62.0), (300.0, 80.0), (600.0, 95.0), (900.0, 100.0))
HEADROOM_ANCHORS: Anchors = ((-0.20, 0.0), (0.0, 50.0), (0.15, 75.0), (0.35, 95.0), (0.60, 100.0))
RENT_COVERAGE_ANCHORS: Anchors = ((0.6, 0.0), (0.9, 35.0), (1.0, 50.0), (1.2, 72.0), (1.5, 90.0), (2.0, 100.0))

PROFIT_MIX = (("cap_rate", 0.30), ("cash_on_cash", 0.30), ("dscr", 0.20), ("cash_flow", 0.20))

# Benchmarks quoted in the explanation bullets.
TARGET_CAP_RATE = 0.06
LENDER_DSCR = 1.20


def curve(value: float, anchors: Anchors) -> float:
    """Piecewise-linear score for ``value``, clamped to the anchor range."""
    if value is None or math.isnan(value):
        return 0.0
    if math.isinf(value):
        return anchors[-1][1] if value > 0 else anchors[0][1]
    if value <= anchors[0][0]:
        return anchors[0][1]
    if value >= anchors[-1][0]:
        return anchors[-1][1]
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if x0 <= value <= x1:
            span = x1 - x0
            if span == 0:
                return y1
            return y0 + (y1 - y0) * (value - x0) / span
    return anchors[-1][1]


def discount_score(inputs: DealInputs, numbers: Underwriting) -> float:
    """How much of the market value you keep as equity on day one."""
    if inputs.market_value <= 0:
        return 50.0
    return curve(numbers.equity_capture / inputs.market_value, DISCOUNT_ANCHORS)


def profitability_score(numbers: Underwriting) -> float:
    parts = {
        "cap_rate": curve(numbers.cap_rate, CAP_RATE_ANCHORS),
        "cash_on_cash": curve(numbers.cash_on_cash, CASH_ON_CASH_ANCHORS),
        "dscr": curve(numbers.dscr, DSCR_ANCHORS),
        "cash_flow": curve(numbers.monthly_cash_flow, CASH_FLOW_ANCHORS),
    }
    return sum(parts[key] * weight for key, weight in PROFIT_MIX)


def affordability_score(inputs: DealInputs, numbers: Underwriting, budget: Budget) -> float:
    """Headroom against the stated budget, or rent coverage when none is set."""
    headrooms: list[float] = []
    if budget.max_price:
        headrooms.append(curve((budget.max_price - inputs.price) / budget.max_price, HEADROOM_ANCHORS))
    if budget.max_cash_to_close:
        headrooms.append(
            curve(
                (budget.max_cash_to_close - numbers.cash_to_close) / budget.max_cash_to_close,
                HEADROOM_ANCHORS,
            )
        )
    if budget.max_monthly_payment:
        headrooms.append(
            curve(
                (budget.max_monthly_payment - numbers.monthly_carrying_cost)
                / budget.max_monthly_payment,
                HEADROOM_ANCHORS,
            )
        )
    if headrooms:
        return sum(headrooms) / len(headrooms)

    if numbers.monthly_carrying_cost <= 0:
        return 100.0
    return curve(inputs.monthly_rent / numbers.monthly_carrying_cost, RENT_COVERAGE_ANCHORS)


def check_budget(inputs: DealInputs, numbers: Underwriting, budget: Budget) -> list[str]:
    """Every budget rule this deal breaks, phrased for a human."""
    misses: list[str] = []
    if budget.max_price and inputs.price > budget.max_price:
        misses.append(f"price ${inputs.price:,.0f} is over the ${budget.max_price:,.0f} limit")
    if budget.max_cash_to_close and numbers.cash_to_close > budget.max_cash_to_close:
        misses.append(
            f"needs ${numbers.cash_to_close:,.0f} at closing, above ${budget.max_cash_to_close:,.0f}"
        )
    if budget.max_monthly_payment and numbers.monthly_carrying_cost > budget.max_monthly_payment:
        misses.append(
            f"carrying cost ${numbers.monthly_carrying_cost:,.0f}/mo is above "
            f"${budget.max_monthly_payment:,.0f}/mo"
        )
    if budget.min_cash_flow is not None and numbers.monthly_cash_flow < budget.min_cash_flow:
        misses.append(
            f"cash flow ${numbers.monthly_cash_flow:,.0f}/mo is under "
            f"${budget.min_cash_flow:,.0f}/mo"
        )
    if budget.min_cap_rate is not None and numbers.cap_rate < budget.min_cap_rate:
        misses.append(
            f"cap rate {numbers.cap_rate:.1%} is under the {budget.min_cap_rate:.1%} floor"
        )
    return misses


def explain(inputs: DealInputs, numbers: Underwriting, breakeven: float | None = None) -> list[str]:
    """Short bullets covering what drives this deal's score."""
    reasons: list[str] = []

    if inputs.market_value > 0:
        equity_pct = numbers.equity_capture / inputs.market_value
        if numbers.equity_capture > 0:
            reasons.append(
                f"${numbers.equity_capture:,.0f} below market value ({equity_pct:.0%} equity at close)"
            )
        elif numbers.equity_capture < 0:
            reasons.append(
                f"${abs(numbers.equity_capture):,.0f} above the estimated market value"
            )

    if numbers.monthly_cash_flow >= 0:
        reasons.append(f"Cash flow ${numbers.monthly_cash_flow:,.0f}/mo")
    else:
        reasons.append(f"Negative cash flow of ${abs(numbers.monthly_cash_flow):,.0f}/mo")

    if numbers.cap_rate >= TARGET_CAP_RATE:
        reasons.append(f"Cap rate {numbers.cap_rate:.1%} clears the {TARGET_CAP_RATE:.0%} target")
    else:
        reasons.append(f"Cap rate {numbers.cap_rate:.1%} is under the {TARGET_CAP_RATE:.0%} target")

    if math.isfinite(numbers.dscr):
        if numbers.dscr < LENDER_DSCR:
            reasons.append(f"DSCR {numbers.dscr:.2f} is below the {LENDER_DSCR:.2f} lenders want")
        else:
            reasons.append(f"DSCR {numbers.dscr:.2f} clears the {LENDER_DSCR:.2f} lender bar")
    else:
        reasons.append("No debt service (all cash)")

    if numbers.max_allowable_offer and inputs.price > numbers.max_allowable_offer:
        gap = inputs.price - numbers.max_allowable_offer
        reasons.append(f"${gap:,.0f} above the 70%-rule offer of ${numbers.max_allowable_offer:,.0f}")

    if inputs.rehab_cost:
        reasons.append(f"Needs ${inputs.rehab_cost:,.0f} of rehab")

    if breakeven and numbers.monthly_cash_flow < 0:
        reasons.append(f"Breaks even at a purchase price of ${breakeven:,.0f}")

    return reasons


def collect_warnings(inputs: DealInputs) -> list[str]:
    """Flag every number that is an estimate rather than a published figure."""
    warnings: list[str] = []
    for field, label in (("price", "Price"), ("rent", "Rent"), ("market_value", "Market value")):
        tag = inputs.provenance.get(field, "")
        if tag and tag != LISTED:
            warnings.append(f"{label} is an estimate ({describe(tag)})")
    return warnings


def score_listing(
    listing: Listing,
    inputs: DealInputs,
    assumptions: Assumptions,
    budget: Budget = Budget(),
    weights: Weights = Weights(),
) -> ScoredDeal:
    """Underwrite one listing and score it."""
    numbers = underwrite(inputs, assumptions)
    w = weights.normalised()

    discount = discount_score(inputs, numbers)
    profitability = profitability_score(numbers)
    affordability = affordability_score(inputs, numbers, budget)
    composite = (
        discount * w.discount + profitability * w.profitability + affordability * w.affordability
    )

    misses = check_budget(inputs, numbers, budget)
    breakeven = breakeven_price(inputs, assumptions)
    return ScoredDeal(
        listing=listing,
        inputs=inputs,
        underwriting=numbers,
        score=ValueScore(
            discount=round(discount, 1),
            profitability=round(profitability, 1),
            affordability=round(affordability, 1),
            composite=round(composite, 1),
        ),
        reasons=explain(inputs, numbers, breakeven),
        warnings=collect_warnings(inputs),
        fits_budget=not misses,
        budget_misses=misses,
        breakeven_price=breakeven,
    )


def rank(deals: list[ScoredDeal]) -> list[ScoredDeal]:
    """Best value first, with deals that break a budget rule sorted last."""
    return sorted(deals, key=lambda d: (not d.fits_budget, -d.score.composite, d.listing.id))
