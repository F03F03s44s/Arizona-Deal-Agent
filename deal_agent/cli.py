"""CLI: rank Arizona deals in the terminal.

Examples:
  python -m deal_agent.cli --top 10
  python -m deal_agent.cli --city Phoenix --max-price 450000
  python -m deal_agent.cli --csv my_redfin_export.csv --top 15
"""

from __future__ import annotations

import argparse

from .models import Deal
from .scoring import rank_deals
from .sources import load_listings


def _fmt_money(x: float) -> str:
    return f"${x:,.0f}"


def _row(rank: int, d: Deal) -> str:
    listing = d.listing
    ppsf = f"{d.price_per_sqft:.0f}" if d.price_per_sqft else "—"
    disc = f"{d.discount_vs_market * 100:+.0f}%" if d.discount_vs_market is not None else "—"
    yld = f"{d.gross_yield * 100:.1f}%" if d.gross_yield is not None else "—"
    beds = f"{listing.beds or '?'}bd/{listing.baths or '?'}ba"
    return (
        f"{rank:>3}  {d.deal_score:>5.1f}  {listing.city:<13} {_fmt_money(listing.price):>10}  "
        f"${ppsf:>4}/sf {disc:>5}  {yld:>5}  {beds:<9} {listing.address}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="deal-agent", description="Rank Arizona deals by value.")
    parser.add_argument("--city", help="filter to one city (e.g. Phoenix)")
    parser.add_argument("--max-price", type=float, help="max list price")
    parser.add_argument("--min-beds", type=int, help="minimum bedrooms")
    parser.add_argument("--top", type=int, default=15, help="show top N deals (default 15)")
    parser.add_argument("--csv", help="rank listings from a CSV export instead of sample data")
    parser.add_argument("--json", dest="json_path", help="rank listings from a JSON file")
    parser.add_argument("--why", action="store_true", help="print the reasons under each deal")
    args = parser.parse_args(argv)

    listings = load_listings(csv_path=args.csv, json_path=args.json_path)
    deals = rank_deals(listings)

    if args.city:
        deals = [d for d in deals if d.listing.city.lower() == args.city.lower()]
    if args.max_price:
        deals = [d for d in deals if d.listing.price <= args.max_price]
    if args.min_beds:
        deals = [d for d in deals if (d.listing.beds or 0) >= args.min_beds]

    print(f"\nArizona Deal Agent — {len(deals)} match(es), showing top {min(args.top, len(deals))}\n")
    print(f"{'#':>3}  {'Score':>5}  {'City':<13} {'Price':>10}  {'$/sqft vs mkt':<13} {'Yield':>5}  {'Size':<9} Address")
    print("-" * 100)
    for rank, deal in enumerate(deals[: args.top], start=1):
        print(_row(rank, deal))
        if args.why:
            for reason in deal.reasons:
                print(f"{'':>12}- {reason}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
