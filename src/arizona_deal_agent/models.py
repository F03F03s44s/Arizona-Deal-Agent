"""Core data structures shared by discovery, underwriting, and scoring."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

# Statewide averages used when a listing does not carry its own carrying costs.
AZ_TAX_RATE = 0.0062
AZ_INSURANCE_RATE = 0.0035


def as_rate(value: float) -> float:
    """Accept a percentage either as ``6.5`` or ``0.065`` and return a fraction.

    Any value above 1 is read as a percentage. Rates at or below 1 are already
    fractions, which makes ``--rate 6.5`` and ``--rate 0.065`` interchangeable.
    """
    value = float(value)
    return value / 100.0 if value > 1 else value


@dataclass(frozen=True)
class Listing:
    """A candidate property returned by a discovery source.

    Only ``id`` and ``source`` are guaranteed. Everything else is optional
    because public feeds vary widely in what they publish; the enrichment step
    fills the gaps and records where each number came from.
    """

    id: str
    source: str
    address: str = ""
    city: str = ""
    state: str = "AZ"
    zip_code: str = ""
    beds: float | None = None
    baths: float | None = None
    sqft: float | None = None
    year_built: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    list_price: float | None = None
    monthly_rent: float | None = None
    market_value: float | None = None
    rehab_cost: float = 0.0
    annual_taxes: float | None = None
    annual_insurance: float | None = None
    monthly_hoa: float = 0.0
    status: str = ""
    url: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        parts = [p for p in (self.address, self.city) if p]
        return ", ".join(parts) if parts else self.id

    @property
    def location(self) -> str:
        city = self.city or "Arizona"
        return f"{city}, {self.state} {self.zip_code}".strip()


@dataclass(frozen=True)
class Assumptions:
    """Financing and operating assumptions for a conventional investor loan."""

    down_payment_pct: float = 0.20
    interest_rate: float = 0.065
    term_years: int = 30
    closing_cost_pct: float = 0.03
    vacancy_pct: float = 0.06
    maintenance_pct: float = 0.08
    management_pct: float = 0.08
    flip_rule: float = 0.70

    def normalised(self) -> Assumptions:
        return replace(
            self,
            down_payment_pct=as_rate(self.down_payment_pct),
            interest_rate=as_rate(self.interest_rate),
            closing_cost_pct=as_rate(self.closing_cost_pct),
            vacancy_pct=as_rate(self.vacancy_pct),
            maintenance_pct=as_rate(self.maintenance_pct),
            management_pct=as_rate(self.management_pct),
            flip_rule=as_rate(self.flip_rule),
        )


@dataclass(frozen=True)
class Budget:
    """Hard limits a deal must respect to be considered buyable."""

    max_price: float | None = None
    max_cash_to_close: float | None = None
    max_monthly_payment: float | None = None
    min_cash_flow: float | None = None
    min_cap_rate: float | None = None

    @property
    def is_set(self) -> bool:
        return any(
            v is not None
            for v in (
                self.max_price,
                self.max_cash_to_close,
                self.max_monthly_payment,
                self.min_cash_flow,
                self.min_cap_rate,
            )
        )


@dataclass(frozen=True)
class Weights:
    """Relative importance of each scoring pillar. Values are normalised."""

    discount: float = 0.25
    profitability: float = 0.40
    affordability: float = 0.35

    def normalised(self) -> Weights:
        total = self.discount + self.profitability + self.affordability
        if total <= 0:
            return Weights()
        return Weights(
            discount=self.discount / total,
            profitability=self.profitability / total,
            affordability=self.affordability / total,
        )


@dataclass(frozen=True)
class DealInputs:
    """The numbers actually underwritten, after enrichment filled the gaps."""

    price: float
    monthly_rent: float
    market_value: float
    rehab_cost: float
    annual_taxes: float
    annual_insurance: float
    monthly_hoa: float
    provenance: dict[str, str] = field(default_factory=dict)

    @property
    def is_fully_estimated(self) -> bool:
        return self.provenance.get("price", "").startswith("estimated")


@dataclass(frozen=True)
class Underwriting:
    """Deterministic finance output for one deal at one set of assumptions."""

    total_cost_basis: float
    down_payment: float
    loan_amount: float
    closing_costs: float
    cash_to_close: float
    monthly_payment: float
    monthly_taxes_insurance: float
    monthly_hoa: float
    monthly_carrying_cost: float
    monthly_cash_flow: float
    gross_annual_rent: float
    effective_gross_rent: float
    annual_operating_expenses: float
    net_operating_income: float
    annual_debt_service: float
    annual_cash_flow: float
    cap_rate: float
    cash_on_cash: float
    dscr: float
    gross_yield: float
    price_to_rent: float
    max_allowable_offer: float
    equity_capture: float


@dataclass(frozen=True)
class ValueScore:
    """Three 0-100 pillars plus the weighted composite used for ranking."""

    discount: float
    profitability: float
    affordability: float
    composite: float


@dataclass(frozen=True)
class ScoredDeal:
    """A candidate with everything needed to rank it and explain the ranking."""

    listing: Listing
    inputs: DealInputs
    underwriting: Underwriting
    score: ValueScore
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fits_budget: bool = True
    budget_misses: list[str] = field(default_factory=list)
    # Highest price that still breaks even each month. The number to offer at
    # when the source never published an ask.
    breakeven_price: float = 0.0

    @property
    def id(self) -> str:
        return self.listing.id
