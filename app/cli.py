"""Command-line interface for ranking and sending Arizona deals."""

from __future__ import annotations

import argparse
from typing import Sequence

from .agent import rank_deals
from .data import DEFAULT_BUDGET, SAMPLE_DEALS
from .models import RankResponse
from .transmit import TransmissionError, transmit

DEFAULT_PROFIT_WEIGHT = 0.6


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app",
        description=(
            "Rank Arizona sample deals by blending profit margin with "
            "affordability, and optionally transmit the result."
        ),
        epilog=(
            "Examples:\n"
            "  python -m app\n"
            "  python -m app rank --budget 2000 --profit-weight 0\n"
            "  python -m app send --inbox --note 'daily pick'\n"
            "  python -m app send --url https://example.com/hooks/deals --format slack\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    rank_parser = sub.add_parser("rank", help="Rank the sample catalog (default).")
    _add_rank_args(rank_parser)

    send_parser = sub.add_parser("send", help="Rank the catalog and transmit the result.")
    _add_rank_args(send_parser)
    dest = send_parser.add_mutually_exclusive_group()
    dest.add_argument("--url", help="POST the payload to this webhook URL.")
    dest.add_argument(
        "--inbox",
        action="store_true",
        help="Deliver to the in-process inbox (default).",
    )
    dest.add_argument(
        "--log-only",
        action="store_true",
        help="Record the payload locally without delivering it.",
    )
    send_parser.add_argument("--note", default=None, help="Optional note attached to the send.")
    send_parser.add_argument(
        "--no-ranking",
        action="store_true",
        help="Transmit only the recommendation, not the full ranked list.",
    )
    send_parser.add_argument(
        "--format",
        choices=("json", "slack"),
        default="json",
        dest="payload_format",
        help="Webhook body format (default: json).",
    )
    return parser


def _add_rank_args(parser: argparse.ArgumentParser) -> None:
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
        help="Print machine-readable JSON instead of a table.",
    )


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


def format_send_report(record) -> str:
    rec_title = record.recommendation_title or "none"
    dest = record.destination
    if dest == "webhook" and record.webhook_host:
        dest = f"webhook ({record.webhook_host})"
    lines = [
        "Arizona Deal Agent — send",
        f"Status: {record.status}   Destination: {dest}",
        f"Recommendation: {rec_title}",
        f"Deals in payload: {record.deal_count}",
    ]
    if record.note:
        lines.append(f"Note: {record.note}")
    if record.error:
        lines.append(f"Error: {record.error}")
    if record.status_code is not None:
        lines.append(f"HTTP: {record.status_code}")
    return "\n".join(lines)


def normalize_argv(argv: Sequence[str] | None) -> list[str]:
    """Treat bare flags as `rank` so `python -m app --budget 2000` still works."""
    args = list(argv) if argv is not None else []
    if not args:
        return ["rank"]
    if args[0] in {"rank", "send"}:
        return args
    return ["rank", *args]


def _require_rank_args(args: argparse.Namespace) -> None:
    if args.budget <= 0:
        raise SystemExit("--budget must be greater than 0")
    if not 0.0 <= args.profit_weight <= 1.0:
        raise SystemExit("--profit-weight must be between 0 and 1")


def run(argv: Sequence[str] | None = None) -> str:
    """Parse arguments and return the output text."""
    args = build_parser().parse_args(normalize_argv(argv))
    command = args.command or "rank"
    _require_rank_args(args)
    ranking = rank_deals(SAMPLE_DEALS, args.budget, args.profit_weight)

    if command == "rank":
        if args.json:
            return ranking.model_dump_json(indent=2)
        return format_report(ranking)

    if args.url:
        destination = "webhook"
    elif args.log_only:
        destination = "log"
    else:
        destination = "inbox"

    try:
        record = transmit(
            ranking,
            destination=destination,
            webhook_url=args.url,
            note=args.note,
            include_ranking=not args.no_ranking,
            payload_format=args.payload_format,
        )
    except TransmissionError as exc:
        raise SystemExit(str(exc)) from exc

    if args.json:
        return record.model_dump_json(indent=2)
    return format_send_report(record)


def main(argv: Sequence[str] | None = None) -> int:
    print(run(argv))
    return 0
