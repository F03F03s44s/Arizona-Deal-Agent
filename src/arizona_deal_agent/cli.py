"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys

from . import __version__, report
from .models import Assumptions, Budget, Weights, as_rate
from .pipeline import DEFAULT_SOURCES, SearchRequest, search
from .sources import available_sources

EPILOG = """\
examples:
  arizona-deal-agent find --top 5
  arizona-deal-agent find --source hud-reo --city Phoenix --city Tucson
  arizona-deal-agent find --max-price 350000 --budget-cash 90000 --min-cash-flow 0
  arizona-deal-agent rank -i my_listings.csv --format csv > ranked.csv
  arizona-deal-agent explain --id AZ-001
  arizona-deal-agent serve --port 8000
"""


def _add_search_options(parser: argparse.ArgumentParser) -> None:
    discovery = parser.add_argument_group("discovery")
    discovery.add_argument(
        "-s", "--source", action="append", default=None, metavar="NAME",
        help="Source to search; repeatable. Built-ins: "
             + ", ".join(available_sources())
             + f". Defaults to {' + '.join(DEFAULT_SOURCES)}.",
    )
    discovery.add_argument(
        "-i", "--input", action="append", default=None, metavar="PATH",
        help="Also read listings from a .csv or .json file; repeatable.",
    )
    discovery.add_argument("--city", action="append", default=None, help="Keep only this city; repeatable.")
    discovery.add_argument("--zip", action="append", default=None, dest="zips", help="Keep only this ZIP; repeatable.")
    discovery.add_argument("--limit", type=int, default=None, help="Max listings to pull per source.")
    discovery.add_argument("--top", type=int, default=None, help="Show only the best N deals.")
    discovery.add_argument(
        "--include-over-budget", action="store_true",
        help="Keep deals that break a budget rule, marked with '!' instead of dropped.",
    )

    budget = parser.add_argument_group("budget (hard filters)")
    budget.add_argument("--max-price", type=float, default=None, help="Highest purchase price.")
    budget.add_argument("--budget-cash", type=float, default=None, help="Cash available at closing.")
    budget.add_argument("--budget-monthly", type=float, default=None, help="Highest monthly carrying cost.")
    budget.add_argument("--min-cash-flow", type=float, default=None, help="Lowest acceptable monthly cash flow.")
    budget.add_argument("--min-cap-rate", type=float, default=None, help="Lowest acceptable cap rate (6 or 0.06).")

    finance = parser.add_argument_group("assumptions (percentages accept 6.5 or 0.065)")
    finance.add_argument("--down-payment", type=float, default=0.20)
    finance.add_argument("--rate", type=float, default=0.065, help="Annual interest rate.")
    finance.add_argument("--term", type=int, default=30, help="Loan term in years.")
    finance.add_argument("--closing-costs", type=float, default=0.03)
    finance.add_argument("--vacancy", type=float, default=0.06)
    finance.add_argument("--maintenance", type=float, default=0.08)
    finance.add_argument("--management", type=float, default=0.08)
    finance.add_argument("--flip-rule", type=float, default=0.70, help="ARV multiplier behind the max offer.")

    weights = parser.add_argument_group("scoring weights (normalised)")
    weights.add_argument("--weight-discount", type=float, default=0.25)
    weights.add_argument("--weight-profit", type=float, default=0.40)
    weights.add_argument("--weight-afford", type=float, default=0.35)

    parser.add_argument(
        "-f", "--format", choices=["table", "json", "csv"], default="table",
        help="Output format (default: table).",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arizona-deal-agent",
        description="Find Arizona property deals and rank them by best value.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    find = subparsers.add_parser(
        "find", help="Search every source and rank what comes back.",
        description="Search the configured sources, underwrite each candidate, and rank by best value.",
        epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_search_options(find)

    rank_cmd = subparsers.add_parser(
        "rank", help="Rank listings you already have (file sources only).",
        description="Same ranking as 'find', but it does not reach out to live sources.",
    )
    _add_search_options(rank_cmd)

    explain = subparsers.add_parser(
        "explain", help="Full underwriting breakdown for one deal.",
        description="Show every number behind one deal's score.",
    )
    explain.add_argument("--id", required=True, help="Listing id, as shown in the ranking.")
    _add_search_options(explain)

    subparsers.add_parser("sources", help="List the available discovery sources.")

    serve = subparsers.add_parser("serve", help="Run the web UI and HTTP API.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")

    return parser


def _request_from(args: argparse.Namespace, live_default: bool) -> SearchRequest:
    specs: list[str] = list(args.source or [])
    specs.extend(args.input or [])
    if not specs:
        specs = list(DEFAULT_SOURCES) if live_default else ["sample"]

    return SearchRequest(
        sources=specs,
        assumptions=Assumptions(
            down_payment_pct=args.down_payment,
            interest_rate=args.rate,
            term_years=args.term,
            closing_cost_pct=args.closing_costs,
            vacancy_pct=args.vacancy,
            maintenance_pct=args.maintenance,
            management_pct=args.management,
            flip_rule=args.flip_rule,
        ),
        budget=Budget(
            max_price=args.max_price,
            max_cash_to_close=args.budget_cash,
            max_monthly_payment=args.budget_monthly,
            min_cash_flow=args.min_cash_flow,
            min_cap_rate=as_rate(args.min_cap_rate) if args.min_cap_rate is not None else None,
        ),
        weights=Weights(
            discount=args.weight_discount,
            profitability=args.weight_profit,
            affordability=args.weight_afford,
        ),
        cities=list(args.city or []),
        zips=list(args.zips or []),
        fetch_limit=args.limit,
        top=args.top,
        include_over_budget=args.include_over_budget,
    )


def _cmd_search(args: argparse.Namespace, live_default: bool) -> int:
    result = search(_request_from(args, live_default))
    print(report.render(result, args.format))
    return 0 if result.deals else 1


def _cmd_explain(args: argparse.Namespace) -> int:
    request = _request_from(args, live_default=True)
    request.include_over_budget = True
    request.top = None
    result = search(request)

    wanted = args.id.strip().lower()
    for deal in result.deals:
        if deal.listing.id.lower() == wanted:
            print(report.render_deal(deal))
            return 0

    print(f"No deal with id '{args.id}'.", file=sys.stderr)
    if result.deals:
        known = ", ".join(deal.listing.id for deal in result.deals[:12])
        print(f"Ids found: {known}", file=sys.stderr)
    return 1


def _cmd_sources() -> int:
    print("Built-in sources:")
    for name, description in available_sources().items():
        print(f"  {name:<14} {description}")
    print("\nAny .csv or .json path also works as a source, with or without a 'file:' prefix.")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print("The web UI needs the extras: pip install -e '.[web]'", file=sys.stderr)
        return 1

    print(f"Arizona Deal Agent UI on http://{args.host}:{args.port}")
    uvicorn.run("arizona_deal_agent.web.app:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "find":
        return _cmd_search(args, live_default=True)
    if args.command == "rank":
        return _cmd_search(args, live_default=False)
    if args.command == "explain":
        return _cmd_explain(args)
    if args.command == "sources":
        return _cmd_sources()
    if args.command == "serve":
        return _cmd_serve(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
