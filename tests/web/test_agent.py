"""Unit tests for the ranking engine."""

from app.agent import rank_deals, score_deal
from app.models import Deal


def _deal(id_: str, cost: float, value: float) -> Deal:
    return Deal(id=id_, title=id_, acquisition_cost=cost, market_value=value)


def test_score_reports_profit_and_margin():
    scored = score_deal(_deal("a", 100, 150), budget=1000)
    assert scored.profit == 50
    assert scored.profit_margin == 0.5
    assert scored.within_budget is True


def test_over_budget_deal_flagged():
    scored = score_deal(_deal("a", 2000, 5000), budget=1000)
    assert scored.within_budget is False
    assert scored.affordability < 0


def test_ranking_prefers_in_budget_deals():
    deals = [
        _deal("cheap-good", 500, 1500),
        _deal("expensive-huge-profit", 5000, 50000),
    ]
    result = rank_deals(deals, budget=1000)
    # The over-budget deal must never be ranked first.
    assert result.ranked[0].within_budget is True
    assert result.recommendation is not None
    assert result.recommendation.deal.id == "cheap-good"


def test_profit_weight_shifts_ranking():
    deals = [
        _deal("affordable", 100, 130),
        _deal("profitable", 900, 1800),
    ]
    profit_first = rank_deals(deals, budget=1000, profit_weight=1.0)
    afford_first = rank_deals(deals, budget=1000, profit_weight=0.0)

    assert profit_first.ranked[0].deal.id == "profitable"
    assert afford_first.ranked[0].deal.id == "affordable"
