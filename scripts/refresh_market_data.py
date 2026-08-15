#!/usr/bin/env python3
"""Rebuild the packaged Arizona market snapshot from Zillow's research files.

The full ZIP-level files cover the whole country and run to ~130 MB, so they
are streamed and filtered down to Arizona rather than vendored wholesale.

    python3 scripts/refresh_market_data.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from arizona_deal_agent import market  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", default="AZ", help="Two-letter state code (default: AZ)")
    parser.add_argument("--out", default=None, help="Snapshot path (default: packaged snapshot)")
    args = parser.parse_args(argv)

    print(f"Downloading Zillow ZHVI and ZORI, filtering to {args.state}...", flush=True)
    payload = market.build_snapshot(state=args.state)
    path = market.write_snapshot(payload, args.out)

    zips = payload["zips"]
    with_value = sum(1 for row in zips.values() if row.get("value"))
    with_rent = sum(1 for row in zips.values() if row.get("rent"))
    print(f"Wrote {path}")
    print(f"  {len(zips)} ZIPs  ({with_value} with a value, {with_rent} with a rent)")
    print(f"  {len(payload['cities'])} cities")
    print(f"  values as of {payload['value_as_of']}, rents as of {payload['rent_as_of']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
