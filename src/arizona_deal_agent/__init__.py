"""Arizona Deal Agent: find Arizona property deals and rank them by best value."""

from .enrich import Enrichment, enrich
from .finance import breakeven_price, monthly_payment, underwrite
from .market import MarketData, ZipMarket, load_snapshot
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
from .pipeline import SearchRequest, SearchResult, search
from .scoring import rank, score_listing
from .sources import available_sources, load_listings

__version__ = "0.1.0"

__all__ = [
    "Assumptions",
    "Budget",
    "DealInputs",
    "Enrichment",
    "Listing",
    "MarketData",
    "ScoredDeal",
    "SearchRequest",
    "SearchResult",
    "Underwriting",
    "ValueScore",
    "Weights",
    "ZipMarket",
    "__version__",
    "available_sources",
    "breakeven_price",
    "enrich",
    "load_listings",
    "load_snapshot",
    "monthly_payment",
    "rank",
    "score_listing",
    "search",
    "underwrite",
]
