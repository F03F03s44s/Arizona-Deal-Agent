"""Core ranking logic for the Arizona Deal Agent.

The agent looks for the "lowest most profitable, most affordable" deal: it
rewards deals with a strong profit margin while penalizing ones that eat up a
large share of the buyer's budget. Both signals are normalized to a 0-1 range
so a single tunable weight can trade profit against affordability.
"""

from __future__ import annotations

from .models import Deal, RankResponse, ScoredDeal


def _profit_margin(deal: Deal) -> float:
    """Profit as a fraction of acquisition cost (can be negative)."""
    return (deal.market_value - deal.acquisition_cost) / deal.acquisition_cost


def _affordability(deal: Deal, budget: float) -> float:
    """1.0 when the deal is free relative to budget, 0.0 when it consumes it all.

    Deals over budget yield a negative affordability so they sort last.
    """
    return 1.0 - (deal.acquisition_cost / budget)


def score_deal(deal: Deal, budget: float, profit_weight: float = 0.6) -> ScoredDeal:
    """Score a single deal against a budget.

    ``profit_weight`` in [0, 1] blends the profit-margin signal with the
    affordability signal. The margin is squashed with a logistic-style clamp so
    a few outsized flips cannot dominate the ranking.
    """
    margin = _profit_margin(deal)
    affordability = _affordability(deal, budget)

    # Normalize margin into 0-1: a 100% margin maps to ~1.0, break-even to 0.5.
    normalized_margin = max(0.0, min(1.0, 0.5 + margin / 2.0))
    normalized_affordability = max(0.0, min(1.0, affordability))

    score = (
        profit_weight * normalized_margin
        + (1.0 - profit_weight) * normalized_affordability
    )

    return ScoredDeal(
        deal=deal,
        profit=round(deal.market_value - deal.acquisition_cost, 2),
        profit_margin=round(margin, 4),
        affordability=round(affordability, 4),
        score=round(score, 4),
        within_budget=deal.acquisition_cost <= budget,
    )


def rank_deals(
    deals: list[Deal], budget: float, profit_weight: float = 0.6
) -> RankResponse:
    """Rank deals best-first and surface the top in-budget recommendation."""
    scored = [score_deal(deal, budget, profit_weight) for deal in deals]
    scored.sort(key=lambda s: (s.within_budget, s.score), reverse=True)

    recommendation = next((s for s in scored if s.within_budget), None)

    return RankResponse(
        budget=budget,
        profit_weight=profit_weight,
        ranked=scored,
        recommendation=recommendation,
    )
