"""Data models for listings and scored deals."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

PropertyType = Literal["single_family", "townhouse", "condo", "multi_family", "manufactured", "land", "other"]


class Listing(BaseModel):
    """A raw for-sale listing, before scoring."""

    id: str
    address: str
    city: str
    state: str = "AZ"
    zip_code: Optional[str] = None
    price: float = Field(gt=0)
    original_price: Optional[float] = None
    beds: Optional[int] = None
    baths: Optional[float] = None
    sqft: Optional[float] = None
    lot_sqft: Optional[float] = None
    year_built: Optional[int] = None
    days_on_market: Optional[int] = None
    property_type: PropertyType = "single_family"
    hoa_monthly: Optional[float] = None
    url: Optional[str] = None

    @property
    def price_per_sqft(self) -> Optional[float]:
        if self.sqft and self.sqft > 0:
            return self.price / self.sqft
        return None


class ScoreBreakdown(BaseModel):
    """Component scores (each 0-100) that make up the composite deal score."""

    value: float
    yield_: float = Field(alias="yield")
    motivation: float
    risk: float

    model_config = {"populate_by_name": True}


class Deal(BaseModel):
    """A listing enriched with valuation metrics and a composite deal score."""

    listing: Listing
    deal_score: float
    breakdown: ScoreBreakdown
    confidence: Literal["high", "medium", "low"]
    price_per_sqft: Optional[float] = None
    market_median_ppsf: Optional[float] = None
    discount_vs_market: Optional[float] = None  # fraction, positive = below market
    est_monthly_rent: Optional[float] = None
    gross_yield: Optional[float] = None  # annual rent / price
    price_cut_pct: Optional[float] = None  # fraction of original price cut so far
    reasons: list[str] = []
