"""Shareable recommendation text for the unified product."""

from __future__ import annotations

from arizona_deal_agent.brand import PRODUCT

from .models import ScoredDeal


def render_transmit(scored: ScoredDeal, *, recipient: str | None = None) -> str:
    """Format a ranked deal as a copy-paste recommendation."""
    deal = scored.deal
    lines: list[str] = []
    if recipient:
        lines.append(f"To: {recipient}")
        lines.append("")
    lines.append(f"{PRODUCT} RECOMMENDATION")
    lines.append("=" * 32)
    lines.append(deal.title)
    if deal.location:
        lines.append(deal.location)
    lines.append("")
    lines.append(f"Asking:       ${deal.acquisition_cost:,.0f}")
    lines.append(f"Comparable:   ${deal.market_value:,.0f}")
    lines.append(f"Profit:       ${scored.profit:,.0f} ({scored.profit_margin * 100:.0f}%)")
    lines.append(f"Score:        {scored.score:.3f}")
    if deal.url:
        lines.append(f"Listing:      {deal.url}")
    lines.append("")
    lines.append(f"— {PRODUCT}")
    return "\n".join(lines)
