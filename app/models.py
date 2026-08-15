"""Pydantic models for the Arizona Deal Agent."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


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
    url: str | None = Field(default=None, description="Source listing URL.")
    location: str | None = Field(default=None, description="Neighborhood or city.")
    source: str = Field(default="manual", description="Origin of the deal.")


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
    refresh: bool = Field(
        default=False,
        description="Force a fresh Craigslist scrape when deals are empty.",
    )
    query: str | None = Field(
        default=None,
        description="Optional Craigslist search query used when deals are empty.",
    )


class RankResponse(BaseModel):
    """Ranked deals plus the agent's top recommendation."""

    budget: float
    profit_weight: float
    ranked: list[ScoredDeal]
    recommendation: ScoredDeal | None = None
    source: str = "craigslist"
    scraped_count: int = 0


class SavedSearchCreate(BaseModel):
    """Create a saved search that emails when a deal scores above threshold."""

    email: EmailStr
    budget: float = Field(..., gt=0)
    profit_weight: float = Field(default=0.6, ge=0, le=1)
    query: str | None = Field(default=None, description="Craigslist query filter.")
    min_score: float = Field(
        default=0.9,
        ge=0,
        le=1,
        description="Email when any in-budget deal scores at or above this.",
    )


class SavedSearch(SavedSearchCreate):
    """Persisted saved search."""

    id: str
    created_at: datetime
    last_checked_at: datetime | None = None
    last_alerted_at: datetime | None = None
    alert_count: int = 0


class SavedSearchListResponse(BaseModel):
    searches: list[SavedSearch]


class AlertCheckResponse(BaseModel):
    checked: int
    alerts_sent: int
    details: list[str] = Field(default_factory=list)
