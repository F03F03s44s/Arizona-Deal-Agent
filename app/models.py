"""Pydantic models for the Arizona Deal Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Deal(BaseModel):
    """A candidate deal the agent can evaluate.

    ``acquisition_cost`` is what it takes to secure the item and ``market_value``
    is what it can realistically be resold for. ``budget`` is the buyer's cash
    ceiling and is used to gauge how affordable the deal is.
    """

    id: str = Field(..., description="Stable identifier for the deal.")
    title: str = Field(..., description="Human-readable name of the deal.")
    category: str = Field(default="general", description="Deal category.")
    acquisition_cost: float = Field(..., gt=0, description="Cost to acquire.")
    market_value: float = Field(..., gt=0, description="Expected resale value.")


class ScoredDeal(BaseModel):
    """A deal enriched with agent scoring metrics."""

    deal: Deal
    profit: float
    profit_margin: float
    affordability: float
    score: float
    within_budget: bool


class RankRequest(BaseModel):
    """Request payload for ranking a set of deals against a budget."""

    budget: float = Field(..., gt=0, description="Buyer cash ceiling.")
    deals: list[Deal] = Field(default_factory=list)
    profit_weight: float = Field(
        default=0.6,
        ge=0,
        le=1,
        description="How much to favor profit over affordability (0-1).",
    )


class RankResponse(BaseModel):
    """Ranked deals plus the agent's top recommendation."""

    budget: float
    profit_weight: float
    ranked: list[ScoredDeal]
    recommendation: ScoredDeal | None = None
