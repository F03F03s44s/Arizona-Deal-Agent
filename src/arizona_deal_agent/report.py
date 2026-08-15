"""Rendering: tables, JSON payloads, CSV, and per-deal breakdowns.

The JSON produced here is what both ``--format json`` and the HTTP API return,
so the CLI and the web UI always describe a deal the same way.
"""

from __future__ import annotations

import csv
import io
import json
import math

from .enrich import LISTED, describe
from .models import ScoredDeal
from .pipeline import SearchResult

ESTIMATED_MARK = "~"


def money(value: float | None, dash: str = "-") -> str:
    if value is None:
        return dash
    return f"-${abs(value):,.0f}" if value < 0 else f"${value:,.0f}"


def percent(value: float | None, digits: int = 1) -> str:
    if value is None or math.isnan(value):
        return "-"
    if math.isinf(value):
        return "n/a"
    return f"{value * 100:.{digits}f}%"


def ratio(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "-"
    return "n/a" if math.isinf(value) else f"{value:.2f}"


def _table(headers: list[str], rows: list[list[str]], aligns: str) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def render(cells: list[str]) -> str:
        out = []
        for index, cell in enumerate(cells):
            out.append(cell.rjust(widths[index]) if aligns[index] == "r" else cell.ljust(widths[index]))
        return "  ".join(out).rstrip()

    lines = [render(headers), render(["-" * w for w in widths])]
    lines.extend(render(row) for row in rows)
    return "\n".join(lines)


def deal_to_dict(deal: ScoredDeal) -> dict:
    """Full structured view of one ranked deal."""
    listing, inputs, numbers, score = deal.listing, deal.inputs, deal.underwriting, deal.score
    return {
        "id": listing.id,
        "source": listing.source,
        "address": listing.address,
        "city": listing.city,
        "state": listing.state,
        "zip_code": listing.zip_code,
        "location": listing.location,
        "status": listing.status,
        "url": listing.url,
        "beds": listing.beds,
        "baths": listing.baths,
        "sqft": listing.sqft,
        "year_built": listing.year_built,
        "latitude": listing.latitude,
        "longitude": listing.longitude,
        "inputs": {
            "price": round(inputs.price, 2),
            "monthly_rent": round(inputs.monthly_rent, 2),
            "market_value": round(inputs.market_value, 2),
            "rehab_cost": round(inputs.rehab_cost, 2),
            "annual_taxes": round(inputs.annual_taxes, 2),
            "annual_insurance": round(inputs.annual_insurance, 2),
            "monthly_hoa": round(inputs.monthly_hoa, 2),
            "price_is_estimated": inputs.provenance.get("price") != LISTED,
            "provenance": inputs.provenance,
            "provenance_labels": {
                key: describe(value)
                for key, value in inputs.provenance.items()
                if key != "market_scope"
            },
        },
        "underwriting": {
            "total_cost_basis": round(numbers.total_cost_basis, 2),
            "down_payment": round(numbers.down_payment, 2),
            "loan_amount": round(numbers.loan_amount, 2),
            "closing_costs": round(numbers.closing_costs, 2),
            "cash_to_close": round(numbers.cash_to_close, 2),
            "monthly_payment": round(numbers.monthly_payment, 2),
            "monthly_carrying_cost": round(numbers.monthly_carrying_cost, 2),
            "monthly_cash_flow": round(numbers.monthly_cash_flow, 2),
            "net_operating_income": round(numbers.net_operating_income, 2),
            "annual_cash_flow": round(numbers.annual_cash_flow, 2),
            "cap_rate": round(numbers.cap_rate, 5),
            "cash_on_cash": round(numbers.cash_on_cash, 5),
            "dscr": None if math.isinf(numbers.dscr) else round(numbers.dscr, 3),
            "gross_yield": round(numbers.gross_yield, 5),
            "price_to_rent": None if math.isinf(numbers.price_to_rent) else round(numbers.price_to_rent, 2),
            "max_allowable_offer": round(numbers.max_allowable_offer, 2),
            "equity_capture": round(numbers.equity_capture, 2),
            "breakeven_price": round(deal.breakeven_price, 2),
        },
        "scores": {
            "discount": score.discount,
            "profitability": score.profitability,
            "affordability": score.affordability,
            "composite": score.composite,
        },
        "reasons": deal.reasons,
        "warnings": deal.warnings,
        "fits_budget": deal.fits_budget,
        "budget_misses": deal.budget_misses,
    }


def result_to_dict(result: SearchResult) -> dict:
    """Structured view of a whole search, including how it was configured."""
    request = result.request
    assumptions = request.assumptions.normalised()
    return {
        "deals": [deal_to_dict(deal) for deal in result.deals],
        "best": deal_to_dict(result.best) if result.best else None,
        "counts": {
            "found": result.found,
            "scored": result.scored,
            "ranked": len(result.deals),
            "filtered_out": result.filtered_out,
            "over_budget": result.over_budget,
        },
        "sources": [
            {"name": report.name, "count": len(report.listings), "error": report.error}
            for report in result.source_reports
        ],
        "market_as_of": result.market_as_of,
        "errors": result.errors,
        "request": {
            "sources": request.sources,
            "cities": request.cities,
            "zips": request.zips,
            "top": request.top,
            "include_over_budget": request.include_over_budget,
            "assumptions": {
                "down_payment_pct": assumptions.down_payment_pct,
                "interest_rate": assumptions.interest_rate,
                "term_years": assumptions.term_years,
                "closing_cost_pct": assumptions.closing_cost_pct,
                "vacancy_pct": assumptions.vacancy_pct,
                "maintenance_pct": assumptions.maintenance_pct,
                "management_pct": assumptions.management_pct,
                "flip_rule": assumptions.flip_rule,
            },
            "budget": {
                "max_price": request.budget.max_price,
                "max_cash_to_close": request.budget.max_cash_to_close,
                "max_monthly_payment": request.budget.max_monthly_payment,
                "min_cash_flow": request.budget.min_cash_flow,
                "min_cap_rate": request.budget.min_cap_rate,
            },
            "weights": {
                "discount": request.weights.discount,
                "profitability": request.weights.profitability,
                "affordability": request.weights.affordability,
            },
        },
    }


def render_table(result: SearchResult) -> str:
    """The default human-readable ranking."""
    if not result.deals:
        return _no_results(result)

    headers = ["#", "SOURCE", "ADDRESS", "CITY", "PRICE", "RENT", "CASH FLOW", "CAP", "CoC", "SCORE"]
    rows: list[list[str]] = []
    for index, deal in enumerate(result.deals, start=1):
        mark = ESTIMATED_MARK if deal.inputs.provenance.get("price") != LISTED else ""
        flag = "" if deal.fits_budget else " !"
        rows.append(
            [
                f"{index}{flag}",
                deal.listing.source,
                deal.listing.address[:34] or "-",
                deal.listing.city or "-",
                mark + money(deal.inputs.price),
                money(deal.inputs.monthly_rent),
                money(deal.underwriting.monthly_cash_flow),
                percent(deal.underwriting.cap_rate),
                percent(deal.underwriting.cash_on_cash),
                f"{deal.score.composite:.1f}",
            ]
        )

    parts = [_table(headers, rows, "rlllrrrrrr"), ""]
    parts.append(_summary_line(result))

    best = result.best
    if best:
        parts.append(f"\nBest value: {best.listing.label} — score {best.score.composite:.1f}/100")
        for reason in best.reasons[:4]:
            parts.append(f"  - {reason}")
        if best.warnings:
            parts.append(f"  ! {'; '.join(best.warnings)}")

    if any(deal.inputs.provenance.get("price") != LISTED for deal in result.deals):
        parts.append(
            f"\n{ESTIMATED_MARK} price estimated from the ZIP's typical home value "
            f"(Zillow ZHVI, {result.market_as_of}); confirm the real ask before offering."
        )
    if result.errors:
        parts.append("\nSource problems:")
        parts.extend(f"  - {error}" for error in result.errors)
    return "\n".join(parts)


def _summary_line(result: SearchResult) -> str:
    bits = [f"Found {result.found} candidate(s)", f"ranked {len(result.deals)}"]
    if result.filtered_out:
        bits.append(f"{result.filtered_out} filtered out by location")
    if result.over_budget:
        state = "shown" if result.request.include_over_budget else "hidden"
        bits.append(f"{result.over_budget} over budget ({state})")
    sourced = ", ".join(
        f"{report.name}={len(report.listings)}" for report in result.source_reports
    )
    return ". ".join([", ".join(bits), f"Sources: {sourced}."])


def _no_results(result: SearchResult) -> str:
    lines = ["No deals matched.", _summary_line(result)]
    if result.over_budget and not result.request.include_over_budget:
        lines.append("Every candidate broke a budget rule. Re-run with --include-over-budget to see them.")
    if result.filtered_out and not result.over_budget:
        lines.append("Every candidate was filtered out by --city/--zip.")
    if result.errors:
        lines.append("Source problems:")
        lines.extend(f"  - {error}" for error in result.errors)
        lines.append("Live sources need network access. Run with --source sample to work offline.")
    return "\n".join(lines)


def render_json(result: SearchResult) -> str:
    return json.dumps(result_to_dict(result), indent=2)


def render_csv(result: SearchResult) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "rank", "id", "source", "address", "city", "zip_code", "price",
            "price_is_estimated", "monthly_rent", "market_value", "cash_to_close",
            "monthly_cash_flow", "cap_rate", "cash_on_cash", "dscr",
            "max_allowable_offer", "breakeven_price", "score_discount",
            "score_profitability", "score_affordability", "score", "fits_budget",
        ]
    )
    for index, deal in enumerate(result.deals, start=1):
        numbers = deal.underwriting
        writer.writerow(
            [
                index, deal.listing.id, deal.listing.source, deal.listing.address,
                deal.listing.city, deal.listing.zip_code, round(deal.inputs.price, 2),
                deal.inputs.provenance.get("price") != LISTED,
                round(deal.inputs.monthly_rent, 2), round(deal.inputs.market_value, 2),
                round(numbers.cash_to_close, 2), round(numbers.monthly_cash_flow, 2),
                round(numbers.cap_rate, 5), round(numbers.cash_on_cash, 5),
                "" if math.isinf(numbers.dscr) else round(numbers.dscr, 3),
                round(numbers.max_allowable_offer, 2), round(deal.breakeven_price, 2),
                deal.score.discount, deal.score.profitability, deal.score.affordability,
                deal.score.composite, deal.fits_budget,
            ]
        )
    return buffer.getvalue().rstrip("\r\n")


def render_deal(deal: ScoredDeal) -> str:
    """Full breakdown of a single deal, the way an underwriter would read it."""
    listing, inputs, numbers, score = deal.listing, deal.inputs, deal.underwriting, deal.score
    lines = [f"{listing.id} - {listing.label}", "=" * max(24, len(listing.label) + len(listing.id) + 3)]

    facts = []
    if listing.beds:
        facts.append(f"{listing.beds:g} bd")
    if listing.baths:
        facts.append(f"{listing.baths:g} ba")
    if listing.sqft:
        facts.append(f"{listing.sqft:,.0f} sqft")
    if listing.year_built:
        facts.append(f"built {listing.year_built}")
    if listing.sqft and inputs.price:
        facts.append(f"{money(inputs.price / listing.sqft)}/sqft")
    if facts:
        lines.append("  " + " | ".join(facts))
    lines.append(f"  {listing.location} | source: {listing.source}" + (f" | {listing.status}" if listing.status else ""))

    def row(label: str, value: str) -> str:
        return f"  {label:<24} {value}"

    lines += ["", "MARKET", row("Scope", inputs.provenance.get("market_scope", "-"))]
    lines.append(row("Typical value", f"{money(inputs.market_value)}  ({describe(inputs.provenance.get('market_value', ''))})"))
    lines.append(row("Typical rent", f"{money(inputs.monthly_rent)}/mo  ({describe(inputs.provenance.get('rent', ''))})"))

    lines += ["", "PURCHASE"]
    lines.append(row("Price", f"{money(inputs.price)}  ({describe(inputs.provenance.get('price', ''))})"))
    lines.append(row("Rehab budget", money(inputs.rehab_cost)))
    lines.append(row("Total cost basis", money(numbers.total_cost_basis)))
    lines.append(row("Down payment", money(numbers.down_payment)))
    lines.append(row("Closing costs", money(numbers.closing_costs)))
    lines.append(row("Cash to close", money(numbers.cash_to_close)))

    lines += ["", "MONTHLY"]
    lines.append(row("Market rent", money(inputs.monthly_rent)))
    lines.append(row("Mortgage payment", money(numbers.monthly_payment)))
    lines.append(row("Taxes + insurance", money(numbers.monthly_taxes_insurance)))
    lines.append(row("HOA", money(numbers.monthly_hoa)))
    lines.append(row("Carrying cost", money(numbers.monthly_carrying_cost)))
    lines.append(row("Cash flow", money(numbers.monthly_cash_flow)))

    lines += ["", "ANNUAL"]
    lines.append(row("Effective gross rent", money(numbers.effective_gross_rent)))
    lines.append(row("Operating expenses", money(numbers.annual_operating_expenses)))
    lines.append(row("Net operating income", money(numbers.net_operating_income)))
    lines.append(row("Debt service", money(numbers.annual_debt_service)))
    lines.append(row("Cash flow", money(numbers.annual_cash_flow)))

    lines += ["", "RETURNS"]
    lines.append(row("Cap rate", percent(numbers.cap_rate, 2)))
    lines.append(row("Cash-on-cash", percent(numbers.cash_on_cash, 2)))
    lines.append(row("DSCR", ratio(numbers.dscr)))
    lines.append(row("Gross yield", percent(numbers.gross_yield, 2)))
    lines.append(row("Price-to-rent", ratio(numbers.price_to_rent)))
    lines.append(row("70%-rule max offer", money(numbers.max_allowable_offer)))
    lines.append(row("Breakeven price", money(deal.breakeven_price)))
    lines.append(row("Equity capture", money(numbers.equity_capture)))

    lines += ["", "SCORES (0-100)"]
    lines.append(row("Discount", f"{score.discount:.1f}"))
    lines.append(row("Profitability", f"{score.profitability:.1f}"))
    lines.append(row("Affordability", f"{score.affordability:.1f}"))
    lines.append(row("Best value", f"{score.composite:.1f}"))

    if deal.reasons:
        lines += ["", "WHY"]
        lines.extend(f"  - {reason}" for reason in deal.reasons)
    if deal.warnings:
        lines += ["", "ESTIMATES USED"]
        lines.extend(f"  ! {warning}" for warning in deal.warnings)
    if deal.budget_misses:
        lines += ["", "BUDGET"]
        lines.extend(f"  x {miss}" for miss in deal.budget_misses)
    return "\n".join(lines)


def render(result: SearchResult, fmt: str) -> str:
    renderers = {"table": render_table, "json": render_json, "csv": render_csv}
    if fmt not in renderers:
        raise ValueError(f"unknown format '{fmt}' (expected table, json, or csv)")
    return renderers[fmt](result)
