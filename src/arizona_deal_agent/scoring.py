"""Turn raw financial metrics into comparable 0-100 scores.

Scores are anchored to fixed industry benchmarks rather than to the rest of the
list. A deal therefore keeps the same score whether it is ranked alone or
against a hundred others, which makes results stable and reproducible.
"""

from __future__ import annotations

from .finance import compute_metrics
from .models import Assumptions, Budget, Listing, Metrics, ScoredDeal, Weights

Curve = tuple[tuple[float, float], ...]

# Each curve maps a metric value to a 0-100 score. Values between two anchors
# are interpolated linearly; values outside the range clamp to the nearest end.
CAP_RATE_CURVE: Curve = ((0.03, 0.0), (0.05, 40.0), (0.07, 70.0), (0.10, 100.0))
CASH_ON_CASH_CURVE: Curve = ((-0.02, 0.0), (0.0, 25.0), (0.05, 60.0), (0.08, 80.0), (0.12, 100.0))
DSCR_CURVE: Curve = ((0.80, 0.0), (1.00, 40.0), (1.25, 75.0), (1.50, 100.0))
MONTHLY_CASH_FLOW_CURVE: Curve = ((-200.0, 0.0), (0.0, 30.0), (200.0, 65.0), (500.0, 100.0))
PRICE_TO_RENT_CURVE: Curve = ((9.0, 100.0), (12.0, 70.0), (15.0, 40.0), (20.0, 0.0))
EQUITY_CAPTURE_CURVE: Curve = ((-0.10, 0.0), (0.0, 50.0), (0.10, 80.0), (0.20, 100.0))
RENT_COVERAGE_CURVE: Curve = ((0.80, 0.0), (1.00, 50.0), (1.20, 80.0), (1.40, 100.0))
# Ratio of a cost to the buyer's limit for it: half the budget scores full marks,
# exactly at budget still passes, and 50% over budget scores zero.
BUDGET_USAGE_CURVE: Curve = ((0.50, 100.0), (0.80, 85.0), (1.00, 60.0), (1.25, 25.0), (1.50, 0.0))

PROFITABILITY_MIX = (("cap_rate", 0.30), ("cash_on_cash", 0.30), ("dscr", 0.20), ("cash_flow", 0.20))


def interpolate(value: float, curve: Curve) -> float:
    """Piecewise-linear lookup against ``curve``, clamped at both ends.

    ``curve`` must be sorted by its first element. Scores may rise or fall as the
    value rises, so both "higher is better" and "lower is better" metrics work.
    """
    if not curve:
        raise ValueError("curve must contain at least one anchor point")
    if value <= curve[0][0]:
        return curve[0][1]
    if value >= curve[-1][0]:
        return curve[-1][1]
    for (low_value, low_score), (high_value, high_score) in zip(curve, curve[1:]):
        if low_value <= value <= high_value:
            span = high_value - low_value
            if span == 0:
                return high_score
            ratio = (value - low_value) / span
            return low_score + ratio * (high_score - low_score)
    return curve[-1][1]


def profitability_score(metrics: Metrics) -> float:
    """Blend of cap rate, cash-on-cash return, DSCR and monthly cash flow."""
    # An all-cash purchase carries no debt, so there is no coverage to fall
    # short of. Scoring its zero DSCR off the curve would punish the safest
    # way to buy.
    coverage = 100.0 if metrics.annual_debt_service <= 0 else interpolate(metrics.dscr, DSCR_CURVE)
    parts = {
        "cap_rate": interpolate(metrics.cap_rate, CAP_RATE_CURVE),
        "cash_on_cash": interpolate(metrics.cash_on_cash, CASH_ON_CASH_CURVE),
        "dscr": coverage,
        "cash_flow": interpolate(metrics.monthly_cash_flow, MONTHLY_CASH_FLOW_CURVE),
    }
    return sum(parts[name] * weight for name, weight in PROFITABILITY_MIX)


def price_score(listing: Listing, metrics: Metrics) -> float:
    """How cheap the asking price is for what the property produces.

    A price can be attractive for either of two reasons: it is low against the
    rent it earns, or it is low against what the finished property is worth. The
    better of the two arguments wins, so supplying an ARV can raise this score
    but never drag down an otherwise strong rental.
    """
    if metrics.price_to_rent is None:
        rent_value = 0.0
    else:
        rent_value = interpolate(metrics.price_to_rent, PRICE_TO_RENT_CURVE)

    if listing.arv is None or metrics.equity_capture is None or listing.arv <= 0:
        return rent_value

    equity_ratio = metrics.equity_capture / listing.arv
    equity_value = interpolate(equity_ratio, EQUITY_CAPTURE_CURVE)
    return max(rent_value, equity_value)


def affordability_score(listing: Listing, metrics: Metrics, budget: Budget) -> float:
    """How comfortably the deal fits the buyer's limits.

    With no budget supplied there is nothing absolute to measure against, so the
    score falls back to rent coverage: a property whose rent covers its own
    carrying cost is affordable to hold regardless of the buyer.
    """
    if budget.is_empty:
        if metrics.rent_coverage is None:
            # Nothing is owed each month, so there is nothing to fall short on.
            return 100.0
        return interpolate(metrics.rent_coverage, RENT_COVERAGE_CURVE)

    usages: list[float] = []
    if budget.max_price is not None:
        usages.append(listing.list_price / budget.max_price)
    if budget.max_monthly_payment is not None:
        usages.append(metrics.monthly_carrying_cost / budget.max_monthly_payment)
    if budget.max_cash_to_close is not None:
        usages.append(metrics.cash_to_close / budget.max_cash_to_close)

    # The tightest constraint decides affordability; a deal you cannot fund is
    # not made affordable by being cheap on some other axis.
    return interpolate(max(usages), BUDGET_USAGE_CURVE)


def build_notes(listing: Listing, metrics: Metrics, budget: Budget) -> list[str]:
    """Short plain-language findings shown next to the numbers."""
    notes: list[str] = []

    if metrics.monthly_cash_flow >= 200:
        notes.append(f"Strong cash flow at ${metrics.monthly_cash_flow:,.0f}/mo")
    elif metrics.monthly_cash_flow >= 0:
        notes.append(f"Thin cash flow at ${metrics.monthly_cash_flow:,.0f}/mo")
    else:
        notes.append(f"Negative cash flow of ${abs(metrics.monthly_cash_flow):,.0f}/mo")

    if metrics.cap_rate >= 0.07:
        notes.append(f"Cap rate {metrics.cap_rate:.1%} beats the 7% target")
    elif metrics.cap_rate < 0.05:
        notes.append(f"Cap rate {metrics.cap_rate:.1%} is below the 5% floor")

    if 0 < metrics.dscr < 1.20:
        notes.append(f"DSCR {metrics.dscr:.2f} is under the 1.20 lenders look for")

    if metrics.equity_capture is not None:
        if metrics.equity_capture > 0:
            notes.append(f"${metrics.equity_capture:,.0f} below the 70%-rule offer")
        else:
            notes.append(f"${abs(metrics.equity_capture):,.0f} above the 70%-rule offer")

    if listing.rehab_cost > 0:
        notes.append(f"Needs ${listing.rehab_cost:,.0f} of rehab")

    if budget.max_cash_to_close is not None and metrics.cash_to_close > budget.max_cash_to_close:
        over = metrics.cash_to_close - budget.max_cash_to_close
        notes.append(f"Cash to close is ${over:,.0f} over budget")
    if budget.max_monthly_payment is not None and metrics.monthly_carrying_cost > budget.max_monthly_payment:
        over = metrics.monthly_carrying_cost - budget.max_monthly_payment
        notes.append(f"Monthly cost is ${over:,.0f} over budget")

    return notes


def score_listing(
    listing: Listing,
    assumptions: Assumptions | None = None,
    budget: Budget | None = None,
    weights: Weights | None = None,
) -> ScoredDeal:
    """Score one listing end to end."""
    assumptions = assumptions or Assumptions()
    budget = budget or Budget()
    normalized_weights = (weights or Weights()).normalized()

    metrics = compute_metrics(listing, assumptions)
    price = price_score(listing, metrics)
    profitability = profitability_score(metrics)
    affordability = affordability_score(listing, metrics, budget)
    composite = (
        price * normalized_weights.price
        + profitability * normalized_weights.profitability
        + affordability * normalized_weights.affordability
    )

    return ScoredDeal(
        listing=listing,
        metrics=metrics,
        price_score=price,
        profitability_score=profitability,
        affordability_score=affordability,
        composite_score=composite,
        qualifies=fits_budget(listing, metrics, budget),
        notes=build_notes(listing, metrics, budget),
    )


def fits_budget(listing: Listing, metrics: Metrics, budget: Budget) -> bool:
    """True when the deal breaks none of the buyer's hard limits."""
    if budget.max_price is not None and listing.list_price > budget.max_price:
        return False
    if budget.max_monthly_payment is not None and metrics.monthly_carrying_cost > budget.max_monthly_payment:
        return False
    if budget.max_cash_to_close is not None and metrics.cash_to_close > budget.max_cash_to_close:
        return False
    return True


def rank_listings(
    listings: list[Listing],
    assumptions: Assumptions | None = None,
    budget: Budget | None = None,
    weights: Weights | None = None,
) -> list[ScoredDeal]:
    """Score every listing and return them best-first."""
    scored = [score_listing(listing, assumptions, budget, weights) for listing in listings]
    return sorted(scored, key=lambda deal: deal.sort_key)
