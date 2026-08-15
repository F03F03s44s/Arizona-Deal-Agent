"""Core data types for the Arizona Deal Agent."""

from __future__ import annotations

from dataclasses import dataclass, field, replace


class DealAgentError(Exception):
    """Base class for every error raised by this package."""


class ValidationError(DealAgentError):
    """A listing or set of assumptions contains impossible values."""


@dataclass(frozen=True)
class Listing:
    """A single property being evaluated.

    Money fields are whole dollars. ``arv`` (after-repair value) is optional and
    only used for flip / wholesale math; buy-and-hold metrics ignore it.
    """

    id: str
    list_price: float
    monthly_rent: float
    address: str = ""
    city: str = ""
    zip_code: str = ""
    beds: float = 0.0
    baths: float = 0.0
    sqft: int = 0
    year_built: int | None = None
    annual_taxes: float = 0.0
    annual_insurance: float = 0.0
    monthly_hoa: float = 0.0
    rehab_cost: float = 0.0
    arv: float | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValidationError("listing id must not be empty")
        if self.list_price <= 0:
            raise ValidationError(f"{self.id}: list_price must be positive, got {self.list_price}")
        for name in ("monthly_rent", "annual_taxes", "annual_insurance", "monthly_hoa", "rehab_cost", "sqft"):
            value = getattr(self, name)
            if value < 0:
                raise ValidationError(f"{self.id}: {name} must not be negative, got {value}")
        if self.arv is not None and self.arv <= 0:
            raise ValidationError(f"{self.id}: arv must be positive when provided, got {self.arv}")

    @property
    def label(self) -> str:
        parts = [part for part in (self.address, self.city) if part]
        return ", ".join(parts) if parts else self.id

    @property
    def price_per_sqft(self) -> float | None:
        if self.sqft <= 0:
            return None
        return self.list_price / self.sqft


@dataclass(frozen=True)
class Assumptions:
    """Financing and operating assumptions applied to every listing.

    Defaults describe a conventional 30-year investor loan on an Arizona rental.
    Override any of them from the CLI when your real numbers differ.
    """

    down_payment_pct: float = 0.20
    interest_rate: float = 0.065
    loan_term_years: int = 30
    closing_cost_pct: float = 0.03
    vacancy_rate: float = 0.06
    maintenance_rate: float = 0.08
    management_rate: float = 0.08
    flip_rule_pct: float = 0.70

    def __post_init__(self) -> None:
        fractions = {
            "down_payment_pct": self.down_payment_pct,
            "closing_cost_pct": self.closing_cost_pct,
            "vacancy_rate": self.vacancy_rate,
            "maintenance_rate": self.maintenance_rate,
            "management_rate": self.management_rate,
            "flip_rule_pct": self.flip_rule_pct,
        }
        for name, value in fractions.items():
            if not 0.0 <= value <= 1.0:
                raise ValidationError(f"{name} must be between 0 and 1, got {value}")
        if self.interest_rate < 0:
            raise ValidationError(f"interest_rate must not be negative, got {self.interest_rate}")
        if self.loan_term_years <= 0:
            raise ValidationError(f"loan_term_years must be positive, got {self.loan_term_years}")
        if self.vacancy_rate + self.maintenance_rate + self.management_rate >= 1.0:
            raise ValidationError("vacancy, maintenance and management rates must sum to less than 1")


@dataclass(frozen=True)
class Budget:
    """What the buyer can actually afford.

    Every field is optional. Supplying a limit turns the matching affordability
    component into an absolute measure ("how much headroom is left?") instead of
    the rent-coverage fallback used when no budget is known.
    """

    max_price: float | None = None
    max_monthly_payment: float | None = None
    max_cash_to_close: float | None = None

    def __post_init__(self) -> None:
        for name in ("max_price", "max_monthly_payment", "max_cash_to_close"):
            value = getattr(self, name)
            if value is not None and value <= 0:
                raise ValidationError(f"{name} must be positive when provided, got {value}")

    @property
    def is_empty(self) -> bool:
        return all(
            getattr(self, name) is None
            for name in ("max_price", "max_monthly_payment", "max_cash_to_close")
        )


@dataclass(frozen=True)
class Weights:
    """Relative importance of the three headline scores.

    The defaults follow the project's goal of surfacing the lowest-priced deal
    that is still profitable and still affordable.
    """

    price: float = 0.25
    profitability: float = 0.40
    affordability: float = 0.35

    def __post_init__(self) -> None:
        for name in ("price", "profitability", "affordability"):
            if getattr(self, name) < 0:
                raise ValidationError(f"weight {name} must not be negative")
        if self.total <= 0:
            raise ValidationError("at least one weight must be greater than zero")

    @property
    def total(self) -> float:
        return self.price + self.profitability + self.affordability

    def normalized(self) -> Weights:
        total = self.total
        return replace(
            self,
            price=self.price / total,
            profitability=self.profitability / total,
            affordability=self.affordability / total,
        )


@dataclass(frozen=True)
class Metrics:
    """Raw, un-scored financial figures for one listing."""

    total_cost_basis: float
    cash_to_close: float
    loan_amount: float
    monthly_mortgage: float
    monthly_carrying_cost: float
    monthly_cash_flow: float
    effective_gross_rent: float
    annual_operating_expenses: float
    net_operating_income: float
    annual_debt_service: float
    annual_cash_flow: float
    cap_rate: float
    cash_on_cash: float
    dscr: float
    price_to_rent: float | None
    rent_coverage: float | None
    max_allowable_offer: float | None
    equity_capture: float | None


@dataclass(frozen=True)
class ScoredDeal:
    """A listing plus its metrics, component scores and composite score."""

    listing: Listing
    metrics: Metrics
    price_score: float
    profitability_score: float
    affordability_score: float
    composite_score: float
    qualifies: bool = True
    notes: list[str] = field(default_factory=list)

    @property
    def sort_key(self) -> tuple[float, float, str]:
        """Highest score first, then cheapest, then id -- fully deterministic."""
        return (-self.composite_score, self.listing.list_price, self.listing.id)
