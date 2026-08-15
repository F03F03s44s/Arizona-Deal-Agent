"""Render scored deals as a table, JSON, CSV, or a single-deal breakdown."""

from __future__ import annotations

import csv
import io
import json
from typing import Sequence

from .models import Assumptions, Budget, ScoredDeal

TABLE_HEADERS = ("#", "ID", "ADDRESS", "CITY", "PRICE", "RENT", "CASH FLOW", "CAP", "CoC", "SCORE")
TABLE_ALIGNMENTS = ("right", "left", "left", "left", "right", "right", "right", "right", "right", "right")


def money(value: float | None, decimals: int = 0) -> str:
    if value is None:
        return "-"
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.{decimals}f}"


def percent(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.{decimals}f}%"


def number(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "-"
    return f"{value:.{decimals}f}"


def _pad(text: str, width: int, align: str) -> str:
    return text.rjust(width) if align == "right" else text.ljust(width)


def format_table(headers: Sequence[str], rows: Sequence[Sequence[str]], alignments: Sequence[str]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    lines = ["  ".join(_pad(h, widths[i], alignments[i]) for i, h in enumerate(headers))]
    lines.append("  ".join("-" * width for width in widths))
    for row in rows:
        lines.append("  ".join(_pad(cell, widths[i], alignments[i]) for i, cell in enumerate(row)))
    return "\n".join(lines)


def render_table(deals: Sequence[ScoredDeal]) -> str:
    if not deals:
        return "No listings matched your filters."

    rows = []
    for rank, deal in enumerate(deals, start=1):
        listing = deal.listing
        rows.append(
            (
                str(rank),
                listing.id,
                listing.address or "-",
                listing.city or "-",
                money(listing.list_price),
                money(listing.monthly_rent),
                money(deal.metrics.monthly_cash_flow),
                percent(deal.metrics.cap_rate),
                percent(deal.metrics.cash_on_cash),
                f"{deal.composite_score:.1f}",
            )
        )
    return format_table(TABLE_HEADERS, rows, TABLE_ALIGNMENTS)


def deal_to_dict(deal: ScoredDeal) -> dict:
    listing = deal.listing
    metrics = deal.metrics
    return {
        "id": listing.id,
        "address": listing.address,
        "city": listing.city,
        "zip_code": listing.zip_code,
        "list_price": round(listing.list_price, 2),
        "monthly_rent": round(listing.monthly_rent, 2),
        "rehab_cost": round(listing.rehab_cost, 2),
        "arv": round(listing.arv, 2) if listing.arv is not None else None,
        "price_per_sqft": round(listing.price_per_sqft, 2) if listing.price_per_sqft else None,
        "scores": {
            "composite": round(deal.composite_score, 2),
            "price": round(deal.price_score, 2),
            "profitability": round(deal.profitability_score, 2),
            "affordability": round(deal.affordability_score, 2),
        },
        "metrics": {
            "total_cost_basis": round(metrics.total_cost_basis, 2),
            "cash_to_close": round(metrics.cash_to_close, 2),
            "loan_amount": round(metrics.loan_amount, 2),
            "monthly_mortgage": round(metrics.monthly_mortgage, 2),
            "monthly_carrying_cost": round(metrics.monthly_carrying_cost, 2),
            "monthly_cash_flow": round(metrics.monthly_cash_flow, 2),
            "net_operating_income": round(metrics.net_operating_income, 2),
            "annual_operating_expenses": round(metrics.annual_operating_expenses, 2),
            "annual_cash_flow": round(metrics.annual_cash_flow, 2),
            "cap_rate": round(metrics.cap_rate, 4),
            "cash_on_cash": round(metrics.cash_on_cash, 4),
            "dscr": round(metrics.dscr, 3),
            "price_to_rent": round(metrics.price_to_rent, 2) if metrics.price_to_rent is not None else None,
            "rent_coverage": round(metrics.rent_coverage, 3) if metrics.rent_coverage is not None else None,
            "max_allowable_offer": (
                round(metrics.max_allowable_offer, 2) if metrics.max_allowable_offer is not None else None
            ),
            "equity_capture": (
                round(metrics.equity_capture, 2) if metrics.equity_capture is not None else None
            ),
        },
        "fits_budget": deal.qualifies,
        "notes": list(deal.notes),
    }


def render_json(deals: Sequence[ScoredDeal]) -> str:
    payload = {
        "count": len(deals),
        "deals": [dict(rank=rank, **deal_to_dict(deal)) for rank, deal in enumerate(deals, start=1)],
    }
    return json.dumps(payload, indent=2)


CSV_COLUMNS = (
    "rank",
    "id",
    "address",
    "city",
    "list_price",
    "monthly_rent",
    "monthly_cash_flow",
    "cap_rate",
    "cash_on_cash",
    "dscr",
    "cash_to_close",
    "composite_score",
    "fits_budget",
)


def render_csv(deals: Sequence[ScoredDeal]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for rank, deal in enumerate(deals, start=1):
        metrics = deal.metrics
        writer.writerow(
            [
                rank,
                deal.listing.id,
                deal.listing.address,
                deal.listing.city,
                f"{deal.listing.list_price:.2f}",
                f"{deal.listing.monthly_rent:.2f}",
                f"{metrics.monthly_cash_flow:.2f}",
                f"{metrics.cap_rate:.4f}",
                f"{metrics.cash_on_cash:.4f}",
                f"{metrics.dscr:.3f}",
                f"{metrics.cash_to_close:.2f}",
                f"{deal.composite_score:.2f}",
                str(deal.qualifies).lower(),
            ]
        )
    return buffer.getvalue().rstrip("\n")


def render_explain(deal: ScoredDeal, assumptions: Assumptions, budget: Budget) -> str:
    listing = deal.listing
    metrics = deal.metrics
    lines: list[str] = []

    lines.append(f"{listing.id} - {listing.label}")
    lines.append("=" * max(40, len(listing.label) + len(listing.id) + 3))

    details = []
    if listing.beds or listing.baths:
        details.append(f"{listing.beds:g} bd / {listing.baths:g} ba")
    if listing.sqft:
        details.append(f"{listing.sqft:,} sqft")
    if listing.year_built:
        details.append(f"built {listing.year_built}")
    if listing.price_per_sqft:
        details.append(f"{money(listing.price_per_sqft, 0)}/sqft")
    if details:
        lines.append("  " + " | ".join(details))
    lines.append("")

    lines.append("PURCHASE")
    lines.append(f"  List price               {money(listing.list_price)}")
    lines.append(f"  Rehab budget             {money(listing.rehab_cost)}")
    lines.append(f"  Total cost basis         {money(metrics.total_cost_basis)}")
    lines.append(f"  Down payment ({percent(assumptions.down_payment_pct, 0)})       {money(listing.list_price * assumptions.down_payment_pct)}")
    lines.append(f"  Closing costs ({percent(assumptions.closing_cost_pct, 0)})       {money(listing.list_price * assumptions.closing_cost_pct)}")
    lines.append(f"  Cash to close            {money(metrics.cash_to_close)}")
    lines.append("")

    lines.append("MONTHLY")
    lines.append(f"  Market rent              {money(listing.monthly_rent)}")
    lines.append(f"  Mortgage payment         {money(metrics.monthly_mortgage)}")
    lines.append(f"  Taxes + insurance        {money((listing.annual_taxes + listing.annual_insurance) / 12)}")
    lines.append(f"  HOA                      {money(listing.monthly_hoa)}")
    lines.append(f"  Carrying cost            {money(metrics.monthly_carrying_cost)}")
    lines.append(f"  Cash flow                {money(metrics.monthly_cash_flow)}")
    lines.append("")

    lines.append("ANNUAL")
    lines.append(f"  Effective gross rent     {money(metrics.effective_gross_rent)}")
    lines.append(f"  Operating expenses       {money(metrics.annual_operating_expenses)}")
    lines.append(f"  Net operating income     {money(metrics.net_operating_income)}")
    lines.append(f"  Debt service             {money(metrics.annual_debt_service)}")
    lines.append(f"  Cash flow                {money(metrics.annual_cash_flow)}")
    lines.append("")

    lines.append("RETURNS")
    lines.append(f"  Cap rate                 {percent(metrics.cap_rate, 2)}")
    lines.append(f"  Cash-on-cash             {percent(metrics.cash_on_cash, 2)}")
    lines.append(f"  DSCR                     {number(metrics.dscr)}")
    lines.append(f"  Price-to-rent            {number(metrics.price_to_rent)}")
    lines.append(f"  Rent coverage            {number(metrics.rent_coverage)}")
    if metrics.max_allowable_offer is not None:
        lines.append(f"  70%-rule max offer       {money(metrics.max_allowable_offer)}")
        lines.append(f"  Equity capture           {money(metrics.equity_capture)}")
    lines.append("")

    lines.append("SCORES (0-100)")
    lines.append(f"  Price                    {deal.price_score:.1f}")
    lines.append(f"  Profitability            {deal.profitability_score:.1f}")
    lines.append(f"  Affordability            {deal.affordability_score:.1f}")
    lines.append(f"  Composite                {deal.composite_score:.1f}")

    if not budget.is_empty:
        lines.append("")
        lines.append("BUDGET")
        lines.append(f"  Fits budget              {'yes' if deal.qualifies else 'no'}")

    if deal.notes:
        lines.append("")
        lines.append("NOTES")
        for note in deal.notes:
            lines.append(f"  - {note}")

    return "\n".join(lines)
