"""Pydantic models for the Arizona Deal Agent."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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


class SendRequest(BaseModel):
    """Rank deals, then transmit the result to a destination."""

    budget: float = Field(..., gt=0, description="Buyer cash ceiling.")
    deals: list[Deal] = Field(default_factory=list)
    profit_weight: float = Field(
        default=0.6,
        ge=0,
        le=1,
        description="How much to favor profit over affordability (0-1).",
    )
    destination: Literal["inbox", "webhook", "log"] = Field(
        default="inbox",
        description="inbox = in-process receiver, webhook = HTTP POST, log = record only.",
    )
    webhook_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Required when destination is webhook.",
    )
    note: str | None = Field(default=None, max_length=280)
    include_ranking: bool = Field(
        default=True,
        description="When false, only the recommendation is transmitted.",
    )
    payload_format: Literal["json", "slack"] = Field(
        default="json",
        description="json is the versioned envelope; slack wraps a text summary.",
    )

    @model_validator(mode="after")
    def webhook_requires_url(self) -> SendRequest:
        if self.destination == "webhook" and not (self.webhook_url or "").strip():
            raise ValueError("webhook_url is required when destination is webhook")
        return self


class TransmissionRecord(BaseModel):
    """Audit record for one send or receive."""

    id: str
    sent_at: datetime
    destination: Literal["inbox", "webhook", "log"]
    status: Literal["sent", "failed", "logged"]
    webhook_host: str | None = None
    status_code: int | None = None
    error: str | None = None
    note: str | None = None
    recommendation_id: str | None = None
    recommendation_title: str | None = None
    deal_count: int = 0
    payload: dict[str, Any]
