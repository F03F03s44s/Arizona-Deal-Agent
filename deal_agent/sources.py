"""Listing data sources.

The MVP ships with a realistic bundled Arizona dataset and a CSV importer
that understands both our own column names and Redfin "Download All" export
headers — so you can point the agent at a real market export today, and add
live API sources behind the same load functions later.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Iterable, Optional

from .models import Listing

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SAMPLE_PATH = DATA_DIR / "sample_listings.json"


def load_sample() -> list[Listing]:
    """Bundled Arizona dataset (see scripts/generate_sample_data.py)."""
    raw = json.loads(SAMPLE_PATH.read_text())
    return [Listing(**item) for item in raw]


def load_json(path: str | Path) -> list[Listing]:
    raw = json.loads(Path(path).read_text())
    return [Listing(**item) for item in raw]


# Maps our field names to acceptable CSV headers (lowercased, stripped).
# Includes Redfin export headers so a "Download All" CSV works unmodified.
_CSV_ALIASES: dict[str, tuple[str, ...]] = {
    "address": ("address",),
    "city": ("city",),
    "state": ("state", "state or province"),
    "zip_code": ("zip_code", "zip", "zip or postal code"),
    "price": ("price", "list price"),
    "original_price": ("original_price", "original list price"),
    "beds": ("beds", "bedrooms"),
    "baths": ("baths", "bathrooms"),
    "sqft": ("sqft", "square feet", "living area"),
    "lot_sqft": ("lot_sqft", "lot size"),
    "year_built": ("year_built", "year built"),
    "days_on_market": ("days_on_market", "days on market", "dom"),
    "property_type": ("property_type", "property type"),
    "hoa_monthly": ("hoa_monthly", "hoa/month", "hoa"),
    "url": ("url",),
}

_REDFIN_TYPE_MAP = {
    "single family residential": "single_family",
    "townhouse": "townhouse",
    "condo/co-op": "condo",
    "multi-family (2-4 unit)": "multi_family",
    "multi-family (5+ unit)": "multi_family",
    "mobile/manufactured home": "manufactured",
    "vacant land": "land",
}


def _num(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", value)
    if cleaned in ("", "-", ".", "-."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _norm_type(value: Optional[str]) -> str:
    if not value:
        return "single_family"
    lowered = value.strip().lower()
    if lowered in _REDFIN_TYPE_MAP:
        return _REDFIN_TYPE_MAP[lowered]
    normalized = lowered.replace(" ", "_").replace("-", "_")
    allowed = {"single_family", "townhouse", "condo", "multi_family", "manufactured", "land", "other"}
    return normalized if normalized in allowed else "other"


def _build_header_map(fieldnames: Iterable[str]) -> dict[str, str]:
    lookup = {name.strip().lower(): name for name in fieldnames if name}
    mapping: dict[str, str] = {}
    for field, aliases in _CSV_ALIASES.items():
        for alias in aliases:
            # Redfin URL header is long ("URL (SEE https://...)") — match by prefix.
            candidates = [k for k in lookup if k == alias or (alias == "url" and k.startswith("url"))]
            if candidates:
                mapping[field] = lookup[candidates[0]]
                break
    return mapping


def load_csv(path: str | Path) -> list[Listing]:
    """Import listings from a CSV file (ours or a Redfin export)."""
    listings: list[Listing] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            return []
        header_map = _build_header_map(reader.fieldnames)
        if "price" not in header_map or "city" not in header_map:
            raise ValueError(
                f"CSV at {path} is missing a recognizable price/city column; "
                f"headers found: {reader.fieldnames}"
            )
        for i, row in enumerate(reader, start=1):
            get = lambda f: row.get(header_map[f]) if f in header_map else None  # noqa: E731
            price = _num(get("price"))
            if not price or price <= 0:
                continue
            beds = _num(get("beds"))
            year = _num(get("year_built"))
            dom = _num(get("days_on_market"))
            listings.append(
                Listing(
                    id=f"CSV-{i:04d}",
                    address=(get("address") or f"Unknown address #{i}").strip(),
                    city=(get("city") or "Unknown").strip().title(),
                    state=(get("state") or "AZ").strip() or "AZ",
                    zip_code=(get("zip_code") or None),
                    price=price,
                    original_price=_num(get("original_price")),
                    beds=int(beds) if beds else None,
                    baths=_num(get("baths")),
                    sqft=_num(get("sqft")),
                    lot_sqft=_num(get("lot_sqft")),
                    year_built=int(year) if year else None,
                    days_on_market=int(dom) if dom is not None else None,
                    property_type=_norm_type(get("property_type")),
                    hoa_monthly=_num(get("hoa_monthly")),
                    url=(get("url") or None),
                )
            )
    return listings


def load_listings(csv_path: str | Path | None = None, json_path: str | Path | None = None) -> list[Listing]:
    """Single entry point used by the API and CLI."""
    if csv_path:
        return load_csv(csv_path)
    if json_path:
        return load_json(json_path)
    return load_sample()
