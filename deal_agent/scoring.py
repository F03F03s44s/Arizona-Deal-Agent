"""Deal scoring: turns raw listings into ranked, explainable deals.

Composite Deal Score (0-100) is a weighted blend of four components:

- value (40%):      price per sqft vs. the city's median. Below market is good.
- yield (30%):      estimated gross rental yield (annual rent / price).
- motivation (20%): seller-motivation signals — days on market and price cuts.
- risk (10%):       property age and HOA drag, as a light capex/carry proxy.

Every component is 0-100 so the blend is easy to reason about, and each deal
carries human-readable reasons so the ranking is never a black box.
"""

from __future__ import annotations

from datetime import date

from .market import estimate_monthly_rent, market_for
from .models import Deal, Listing, ScoreBreakdown

WEIGHTS = {"value": 0.40, "yield": 0.30, "motivation": 0.20, "risk": 0.10}

NEUTRAL = 50.0  # used when a component can't be computed


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def score_value(discount_vs_market: float | None) -> float:
    """50 at market price; +2.5 pts per 1% below market (100 at 20% below)."""
    if discount_vs_market is None:
        return NEUTRAL
    return _clamp(50.0 + discount_vs_market * 250.0)


def score_yield(gross_yield: float | None) -> float:
    """0 at a 3% gross yield, 100 at 9%+ (AZ long-term rentals sit in between)."""
    if gross_yield is None:
        return NEUTRAL
    return _clamp((gross_yield - 0.03) / 0.06 * 100.0)


def score_motivation(days_on_market: int | None, price_cut_pct: float | None) -> float:
    """Longer time on market and bigger price cuts mean more negotiating room."""
    dom = min(max(days_on_market or 0, 0), 120)
    dom_component = dom / 120.0 * 60.0
    cut = min(max(price_cut_pct or 0.0, 0.0), 0.10)
    cut_component = cut / 0.10 * 40.0
    return _clamp(dom_component + cut_component)


def score_risk(year_built: int | None, hoa_monthly: float | None, today: date | None = None) -> float:
    """Newer + low-HOA scores high; old housing stock implies capex risk."""
    score = 100.0
    if year_built:
        age = max(0, (today or date.today()).year - year_built)
        score -= _clamp((age - 10) * 1.1, 0.0, 55.0)
    else:
        score = NEUTRAL
    if hoa_monthly:
        score -= _clamp(hoa_monthly / 10.0, 0.0, 25.0)
    return _clamp(score)


def score_listing(listing: Listing, today: date | None = None) -> Deal:
    """Compute metrics, component scores, and the composite deal score."""
    market = market_for(listing.city)
    ppsf = listing.price_per_sqft

    discount = None if ppsf is None else 1.0 - (ppsf / market.median_ppsf)

    est_rent = None
    gross_yield = None
    if listing.sqft and listing.sqft > 0:
        est_rent = estimate_monthly_rent(listing.city, listing.sqft, listing.beds)
        gross_yield = est_rent * 12.0 / listing.price

    price_cut = None
    if listing.original_price and listing.original_price > listing.price:
        price_cut = (listing.original_price - listing.price) / listing.original_price

    components = ScoreBreakdown(
        value=round(score_value(discount), 1),
        yield_=round(score_yield(gross_yield), 1),
        motivation=round(score_motivation(listing.days_on_market, price_cut), 1),
        risk=round(score_risk(listing.year_built, listing.hoa_monthly, today), 1),
    )
    deal_score = round(
        components.value * WEIGHTS["value"]
        + components.yield_ * WEIGHTS["yield"]
        + components.motivation * WEIGHTS["motivation"]
        + components.risk * WEIGHTS["risk"],
        1,
    )

    missing = sum(1 for v in (listing.sqft, listing.year_built, listing.days_on_market) if not v)
    confidence = "high" if missing == 0 else ("medium" if missing == 1 else "low")

    return Deal(
        listing=listing,
        deal_score=deal_score,
        breakdown=components,
        confidence=confidence,
        price_per_sqft=None if ppsf is None else round(ppsf, 2),
        market_median_ppsf=market.median_ppsf,
        discount_vs_market=None if discount is None else round(discount, 4),
        est_monthly_rent=None if est_rent is None else round(est_rent),
        gross_yield=None if gross_yield is None else round(gross_yield, 4),
        price_cut_pct=None if price_cut is None else round(price_cut, 4),
        reasons=_reasons(listing, discount, gross_yield, price_cut),
    )


def _reasons(
    listing: Listing,
    discount: float | None,
    gross_yield: float | None,
    price_cut: float | None,
) -> list[str]:
    reasons: list[str] = []
    if discount is not None:
        pct = abs(discount) * 100
        if discount >= 0.02:
            reasons.append(f"{pct:.0f}% below {listing.city} median $/sqft")
        elif discount <= -0.02:
            reasons.append(f"{pct:.0f}% above {listing.city} median $/sqft")
        else:
            reasons.append(f"Priced at {listing.city} market $/sqft")
    else:
        reasons.append("No sqft reported — value vs. market unknown")
    if gross_yield is not None:
        reasons.append(f"Est. gross rental yield {gross_yield * 100:.1f}%")
    if listing.days_on_market is not None and listing.days_on_market >= 45:
        reasons.append(f"{listing.days_on_market} days on market — room to negotiate")
    if price_cut:
        reasons.append(f"Price already cut {price_cut * 100:.1f}%")
    if listing.hoa_monthly and listing.hoa_monthly >= 200:
        reasons.append(f"Watch: ${listing.hoa_monthly:.0f}/mo HOA")
    if listing.year_built and listing.year_built < 1980:
        reasons.append(f"Watch: built {listing.year_built}, budget for capex")
    return reasons


def rank_deals(listings: list[Listing], today: date | None = None) -> list[Deal]:
    """Score every listing and return them best-deal-first."""
    deals = [score_listing(listing, today) for listing in listings]
    deals.sort(key=lambda d: (-d.deal_score, d.listing.price))
    return deals
