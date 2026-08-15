"""Command line entry point for the Arizona Deal Agent."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import __version__
from .howto import (
    DEFAULT_LISTINGS,
    format_command,
    is_known_scenario,
    render_howto,
    scenario_argv,
    unknown_scenario_message,
)
from .models import Assumptions, Budget, DealAgentError, Listing, ScoredDeal, Weights
from .report import deal_to_dict, render_csv, render_explain, render_json, render_table, render_transmit
from .scoring import rank_listings, score_listing
from .sources import DEFAULT_INSURANCE_RATE, DEFAULT_TAX_RATE, load_listings

PROGRAM = "arizona-deal-agent"


def fraction(text: str) -> float:
    """Accept ``0.065``, ``6.5`` or ``6.5%`` and always return a fraction.

    Anything greater than 1 is read as a percentage, which is how people
    normally type a down payment or an interest rate.
    """
    cleaned = text.strip().rstrip("%")
    try:
        value = float(cleaned)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"'{text}' is not a number") from exc
    if text.strip().endswith("%") or value > 1:
        value /= 100
    if value < 0:
        raise argparse.ArgumentTypeError(f"'{text}' must not be negative")
    return value


def dollars(text: str) -> float:
    cleaned = text.strip().replace("$", "").replace(",", "")
    try:
        return float(cleaned)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"'{text}' is not a dollar amount") from exc


def add_assumption_options(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("financing assumptions")
    group.add_argument("--down-payment", type=fraction, default=0.20, metavar="PCT", help="down payment share (default: 20%%)")
    group.add_argument("--rate", type=fraction, default=0.065, metavar="PCT", help="annual interest rate (default: 6.5%%)")
    group.add_argument("--term", type=int, default=30, metavar="YEARS", help="loan term in years (default: 30)")
    group.add_argument("--closing-costs", type=fraction, default=0.03, metavar="PCT", help="closing costs as a share of price (default: 3%%)")
    group.add_argument("--vacancy", type=fraction, default=0.06, metavar="PCT", help="vacancy allowance (default: 6%%)")
    group.add_argument("--maintenance", type=fraction, default=0.08, metavar="PCT", help="maintenance reserve, share of rent (default: 8%%)")
    group.add_argument("--management", type=fraction, default=0.08, metavar="PCT", help="property management, share of rent (default: 8%%)")
    group.add_argument("--flip-rule", type=fraction, default=0.70, metavar="PCT", help="ARV multiplier for the max offer (default: 70%%)")


def add_budget_options(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("budget limits")
    group.add_argument("--max-price", type=dollars, metavar="USD", help="highest list price you will pay")
    group.add_argument("--budget-monthly", type=dollars, metavar="USD", help="highest monthly carrying cost you can hold")
    group.add_argument("--budget-cash", type=dollars, metavar="USD", help="cash you have available to close")


def add_weight_options(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("score weights")
    group.add_argument("--weight-price", type=float, default=0.25, metavar="W", help="weight on the price score (default: 0.25)")
    group.add_argument("--weight-profit", type=float, default=0.40, metavar="W", help="weight on the profitability score (default: 0.40)")
    group.add_argument("--weight-afford", type=float, default=0.35, metavar="W", help="weight on the affordability score (default: 0.35)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description="Rank Arizona property deals by price, profitability and affordability.",
        epilog=(
            "How to use:\n"
            "  arizona-deal-agent howto\n"
            "  arizona-deal-agent howto --run balanced\n"
            "  arizona-deal-agent rank -i data/sample_listings.csv --top 5\n"
            "  arizona-deal-agent transmit -i data/sample_listings.csv --to 'Investment team'\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"{PROGRAM} {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rank = subparsers.add_parser("rank", help="score a file of listings and show the best deals")
    rank.add_argument("-i", "--input", required=True, metavar="PATH", help="listings file (.csv or .json)")
    rank.add_argument("-n", "--top", type=int, metavar="N", help="show only the top N deals")
    rank.add_argument("-f", "--format", choices=("table", "json", "csv"), default="table", help="output format (default: table)")
    rank.add_argument("--city", action="append", metavar="CITY", help="keep only this city (repeatable)")
    rank.add_argument("--min-cash-flow", type=dollars, metavar="USD", help="drop deals below this monthly cash flow")
    rank.add_argument("--min-cap-rate", type=fraction, metavar="PCT", help="drop deals below this cap rate")
    rank.add_argument("--include-over-budget", action="store_true", help="keep deals that break a budget limit instead of dropping them")
    add_budget_options(rank)
    add_assumption_options(rank)
    add_weight_options(rank)

    explain = subparsers.add_parser("explain", help="show the full breakdown for one listing")
    explain.add_argument("-i", "--input", required=True, metavar="PATH", help="listings file (.csv or .json)")
    explain.add_argument("--id", required=True, metavar="ID", help="id of the listing to explain")
    add_budget_options(explain)
    add_assumption_options(explain)
    add_weight_options(explain)

    score = subparsers.add_parser("score", help="score a single deal typed on the command line")
    score.add_argument("--price", type=dollars, required=True, metavar="USD", help="list price")
    score.add_argument("--rent", type=dollars, required=True, metavar="USD", help="expected monthly rent")
    score.add_argument("--taxes", type=dollars, metavar="USD", help=f"annual property taxes (default: {DEFAULT_TAX_RATE:.2%} of price)")
    score.add_argument("--insurance", type=dollars, metavar="USD", help=f"annual insurance (default: {DEFAULT_INSURANCE_RATE:.2%} of price)")
    score.add_argument("--hoa", type=dollars, default=0.0, metavar="USD", help="monthly HOA dues (default: 0)")
    score.add_argument("--rehab", type=dollars, default=0.0, metavar="USD", help="rehab budget (default: 0)")
    score.add_argument("--arv", type=dollars, metavar="USD", help="after-repair value, enables the 70%% rule")
    score.add_argument("--address", default="Ad-hoc deal", metavar="TEXT", help="label for the output")
    score.add_argument("--city", default="", metavar="CITY", help="city name for the output")
    score.add_argument("--sqft", type=int, default=0, metavar="N", help="living area in square feet")
    add_budget_options(score)
    add_assumption_options(score)
    add_weight_options(score)

    transmit = subparsers.add_parser(
        "transmit",
        help="format the top deal as a shareable recommendation message",
    )
    transmit.add_argument("-i", "--input", required=True, metavar="PATH", help="listings file (.csv or .json)")
    transmit.add_argument("--to", metavar="RECIPIENT", help="optional recipient name for the message header")
    transmit.add_argument(
        "-f",
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    transmit.add_argument("--city", action="append", metavar="CITY", help="keep only this city (repeatable)")
    transmit.add_argument("--min-cash-flow", type=dollars, metavar="USD", help="drop deals below this monthly cash flow")
    transmit.add_argument("--min-cap-rate", type=fraction, metavar="PCT", help="drop deals below this cap rate")
    transmit.add_argument(
        "--include-over-budget",
        action="store_true",
        help="allow deals that break a budget limit instead of dropping them",
    )
    add_budget_options(transmit)
    add_assumption_options(transmit)
    add_weight_options(transmit)

    howto = subparsers.add_parser(
        "howto",
        help="print How to use, or run a named ranking scenario",
    )
    howto.add_argument(
        "-i",
        "--input",
        default=DEFAULT_LISTINGS,
        metavar="PATH",
        help=f"listings file used by --run (default: {DEFAULT_LISTINGS})",
    )
    howto.add_argument(
        "--run",
        metavar="SCENARIO",
        help="run a named scenario: balanced, profit, affordability, or tight",
    )

    return parser


def assumptions_from_args(args: argparse.Namespace) -> Assumptions:
    return Assumptions(
        down_payment_pct=args.down_payment,
        interest_rate=args.rate,
        loan_term_years=args.term,
        closing_cost_pct=args.closing_costs,
        vacancy_rate=args.vacancy,
        maintenance_rate=args.maintenance,
        management_rate=args.management,
        flip_rule_pct=args.flip_rule,
    )


def budget_from_args(args: argparse.Namespace) -> Budget:
    return Budget(
        max_price=args.max_price,
        max_monthly_payment=args.budget_monthly,
        max_cash_to_close=args.budget_cash,
    )


def weights_from_args(args: argparse.Namespace) -> Weights:
    return Weights(
        price=args.weight_price,
        profitability=args.weight_profit,
        affordability=args.weight_afford,
    )


def apply_filters(deals: list[ScoredDeal], args: argparse.Namespace) -> list[ScoredDeal]:
    selected = deals

    if args.city:
        wanted = {city.strip().lower() for city in args.city}
        selected = [deal for deal in selected if deal.listing.city.lower() in wanted]
    if args.min_cash_flow is not None:
        selected = [deal for deal in selected if deal.metrics.monthly_cash_flow >= args.min_cash_flow]
    if args.min_cap_rate is not None:
        selected = [deal for deal in selected if deal.metrics.cap_rate >= args.min_cap_rate]
    if not args.include_over_budget:
        selected = [deal for deal in selected if deal.qualifies]
    top = getattr(args, "top", None)
    if top is not None:
        if top <= 0:
            raise DealAgentError("--top must be a positive number")
        selected = selected[:top]

    return selected


def run_rank(args: argparse.Namespace) -> int:
    listings = load_listings(args.input)
    deals = rank_listings(listings, assumptions_from_args(args), budget_from_args(args), weights_from_args(args))
    selected = apply_filters(deals, args)

    if args.format == "json":
        print(render_json(selected))
    elif args.format == "csv":
        print(render_csv(selected))
    else:
        print(render_table(selected))
        if selected:
            print()
            print(f"Scored {len(listings)} listing(s), showing {len(selected)}. Best: {selected[0].listing.label}.")
            for note in selected[0].notes:
                print(f"  - {note}")
    return 0


def run_explain(args: argparse.Namespace) -> int:
    listings = load_listings(args.input)
    matches = [listing for listing in listings if listing.id.lower() == args.id.lower()]
    if not matches:
        available = ", ".join(listing.id for listing in listings[:10])
        raise DealAgentError(f"no listing with id '{args.id}'. Available ids include: {available}")

    assumptions = assumptions_from_args(args)
    budget = budget_from_args(args)
    deal = score_listing(matches[0], assumptions, budget, weights_from_args(args))
    print(render_explain(deal, assumptions, budget))
    return 0


def run_transmit(args: argparse.Namespace) -> int:
    import json

    listings = load_listings(args.input)
    deals = rank_listings(listings, assumptions_from_args(args), budget_from_args(args), weights_from_args(args))
    selected = apply_filters(deals, args)

    if not selected:
        raise DealAgentError("no listings matched your filters; nothing to transmit")

    top = selected[0]
    if args.format == "json":
        payload = {
            "recipient": args.to,
            "recommendation": deal_to_dict(top),
        }
        print(json.dumps(payload, indent=2))
    else:
        print(render_transmit(top, recipient=args.to))
    return 0


def run_howto(args: argparse.Namespace) -> int:
    if args.run is None:
        print(render_howto(args.input))
        return 0
    if not is_known_scenario(args.run):
        raise DealAgentError(unknown_scenario_message(args.run))

    argv = scenario_argv(args.run, args.input)
    print(f"How to use — {args.run}")
    print(f"$ {format_command(argv)}")
    print()
    return main(argv)


def run_score(args: argparse.Namespace) -> int:
    listing = Listing(
        id="ad-hoc",
        address=args.address,
        city=args.city,
        list_price=args.price,
        monthly_rent=args.rent,
        sqft=args.sqft,
        annual_taxes=args.taxes if args.taxes is not None else round(args.price * DEFAULT_TAX_RATE, 2),
        annual_insurance=(
            args.insurance if args.insurance is not None else round(args.price * DEFAULT_INSURANCE_RATE, 2)
        ),
        monthly_hoa=args.hoa,
        rehab_cost=args.rehab,
        arv=args.arv,
    )
    assumptions = assumptions_from_args(args)
    budget = budget_from_args(args)
    deal = score_listing(listing, assumptions, budget, weights_from_args(args))
    print(render_explain(deal, assumptions, budget))
    return 0


COMMANDS = {
    "rank": run_rank,
    "explain": run_explain,
    "score": run_score,
    "transmit": run_transmit,
    "howto": run_howto,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except DealAgentError as exc:
        print(f"{PROGRAM}: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
