"""Arizona Deal Agent -- find Arizona deals and rank them by best value."""

from .finance import compute_metrics
from .models import Assumptions, Budget, DealAgentError, Listing, Metrics, ScoredDeal, ValidationError, Weights
from .scoring import rank_listings, score_listing
from .sources import ListingParseError, default_sample_path, load_listings

__version__ = "0.1.0"

__all__ = [
    "Assumptions",
    "Budget",
    "DealAgentError",
    "Listing",
    "ListingParseError",
    "Metrics",
    "ScoredDeal",
    "ValidationError",
    "Weights",
    "compute_metrics",
    "default_sample_path",
    "load_listings",
    "rank_listings",
    "score_listing",
    "__version__",
]
