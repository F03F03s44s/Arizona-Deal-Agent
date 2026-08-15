"""Pydantic models for the Arizona Deal Agent."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class Deal(BaseModel):
    """A candidate deal the agent can evaluate.

    ``acquisition_cost`` is the seller's asking price and ``market_value`` is
    what comparable listings are going for. ``budget`` is the buyer's cash
    ceiling and is used to gauge how affordable the deal is.
    """

    id: str = Field(..., description="Stable identifier for the deal.")
    title: str = Field(..., description="Human-readable name of the deal.")
    category: str = Field(default="general", description="Deal category.")
    acquisition_cost: float = Field(..., gt=0, description="Cost to acquire.")
    market_value: float = Field(..., gt=0, description="Expected resale value.")
    url: str | None = Field(default=None, description="Link to the source listing.")
    location: str | None = Field(default=None, description="Where the item is.")
    posted_at: datetime | None = Field(default=None, description="Listing timestamp.")
    source: str = Field(default="sample", description="Where the deal came from.")
    comparable_count: int = Field(
        default=0, description="How many comparable listings set the market value."
    )


class ScoredDeal(BaseModel):
    """A deal enriched with agent scoring metrics."""

    deal: Deal
    profit: float
    profit_margin: float
    affordability: float
    score: float
    within_budget: bool


class RankRequest(BaseModel):
    """Request payload for ranking a set of deals against a budget.

    When ``deals`` is empty the agent sources them itself, scraping ``query``
    from Craigslist. Ranking a cached scrape is pure arithmetic, which is what
    lets the UI re-rank on every slider tick.
    """

    budget: float = Field(..., gt=0, description="Buyer cash ceiling.")
    deals: list[Deal] = Field(default_factory=list)
    profit_weight: float = Field(
        default=0.6,
        ge=0,
        le=1,
        description="How much to favor profit over affordability (0-1).",
    )
    query: str | None = Field(
        default=None, description="Craigslist search to source deals from."
    )


class RankResponse(BaseModel):
    """Ranked deals plus the agent's top recommendation."""

    budget: float
    profit_weight: float
    ranked: list[ScoredDeal]
    recommendation: ScoredDeal | None = None
    source: str = Field(default="sample", description="Where the deals came from.")
    query: str | None = None
    warning: str | None = Field(
        default=None, description="Set when the agent fell back to sample data."
    )


class DealsResponse(BaseModel):
    """Deals the agent sourced for a query, before any ranking."""

    budget: float
    query: str | None = None
    source: str = "sample"
    deals: list[Deal] = Field(default_factory=list)
    warning: str | None = None


class SavedSearchCreate(BaseModel):
    """A standing search the agent re-runs and emails alerts for."""

    query: str = Field(..., min_length=1, description="Craigslist search terms.")
    email: EmailStr = Field(..., description="Where alerts are sent.")
    budget: float = Field(default=15000.0, gt=0)
    profit_weight: float = Field(default=0.6, ge=0, le=1)
    min_score: float = Field(
        default=0.9, ge=0, le=1, description="Alert when a deal scores above this."
    )


class SavedSearch(SavedSearchCreate):
    """A persisted saved search."""

    id: str
    created_at: datetime
    last_run_at: datetime | None = None
    # Deal ids already emailed, so a standing search does not re-alert on the
    # same listing every poll.
    notified_deal_ids: list[str] = Field(default_factory=list)


class Alert(BaseModel):
    """A record of one alert email the agent sent (or attempted)."""

    id: str
    saved_search_id: str
    query: str
    email: str
    subject: str
    body: str
    sent_at: datetime
    delivered: bool
    transport: str
    error: str | None = None
    deal_ids: list[str] = Field(default_factory=list)


class SavedSearchRunResult(BaseModel):
    """Outcome of running one saved search."""

    saved_search_id: str
    query: str
    deals_considered: int
    matches: list[ScoredDeal] = Field(default_factory=list)
    new_matches: list[ScoredDeal] = Field(default_factory=list)
    alert: Alert | None = None
    warning: str | None = None
