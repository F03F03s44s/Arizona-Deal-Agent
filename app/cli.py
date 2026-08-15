"""Command-line interface for ranking Arizona deals."""

from __future__ import annotations

import argparse
from typing import Sequence

from .agent import rank_deals
from .data import DEFAULT_BUDGET, SAMPLE_DEALS
from .models import RankResponse

DEFAULT_PROFIT_WEIGHT = 0.6


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app",
        description=(
            "Rank Arizona sample deals by blending profit margin with "
            "affordability. Over-budget deals are listed last and never recommended."
        ),
        epilog=(
            "Examples:\n"
            "  python -m app\n"
            "  python -m app --budget 2000 --profit-weight 0\n"
            "  python -m app --budget 15000 --profit-weight 1 --json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=DEFAULT_BUDGET,
        help=f"Buyer cash ceiling (default: {DEFAULT_BUDGET:.0f}).",
    )
    parser.add_argument(
        "--profit-weight",
        type=float,
        default=DEFAULT_PROFIT_WEIGHT,
        metavar="WEIGHT",
        help=(
            "0 = prefer leftover budget, 1 = prefer profit margin "
            f"(default: {DEFAULT_PROFIT_WEIGHT})."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full ranking as JSON.",
    )
    return parser


def format_money(amount: float) -> str:
    return f"${amount:,.0f}"


def format_report(result: RankResponse) -> str:
    """Render a human-readable ranking for the terminal."""
    lines = [
        "Arizona Deal Agent",
        f"Budget: {format_money(result.budget)}   "
        f"Profit weight: {result.profit_weight:.2f}",
        "",
    ]
    rec = result.recommendation
    if rec is None:
        lines.append("Recommendation: none — every deal is over budget.")
    else:
        lines.append(f"Recommendation: {rec.deal.title}")
        lines.append(
            f"  Profit {format_money(rec.profit)}  ·  "
            f"margin {rec.profit_margin * 100:.0f}%  ·  "
            f"cost {format_money(rec.deal.acquisition_cost)}  ·  "
            f"score {rec.score:.3f}"
        )
    lines.append("")
    lines.append(
        f"{'#':<3} {'Deal':<42} {'Cost':>10} {'Profit':>10} {'Score':>7}  Budget"
    )
    lines.append("-" * 86)
    for index, scored in enumerate(result.ranked, start=1):
        flag = "in" if scored.within_budget else "over"
        title = scored.deal.title
        if len(title) > 42:
            title = title[:39] + "..."
        lines.append(
            f"{index:<3} {title:<42} {format_money(scored.deal.acquisition_cost):>10} "
            f"{format_money(scored.profit):>10} {scored.score:>7.3f}  {flag}"
        )
    return "\n".join(lines)


def run(argv: Sequence[str] | None = None) -> str:
    """Parse arguments, rank the sample catalog, and return the output text."""
    args = build_parser().parse_args(argv)
    if args.budget <= 0:
        raise SystemExit("--budget must be greater than 0")
    if not 0.0 <= args.profit_weight <= 1.0:
        raise SystemExit("--profit-weight must be between 0 and 1")

    result = rank_deals(SAMPLE_DEALS, args.budget, args.profit_weight)
    if args.json:
        return result.model_dump_json(indent=2)
    return format_report(result)


def main(argv: Sequence[str] | None = None) -> int:
    print(run(argv))
    return 0
