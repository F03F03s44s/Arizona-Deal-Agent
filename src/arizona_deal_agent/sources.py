"""Load listings from the files you already have.

CSV and JSON are supported. Only ``id``, ``list_price`` and ``monthly_rent`` are
required; anything else is optional and either defaults to zero or is estimated
from the price. Common column aliases (``price``, ``rent``, ``hoa`` ...) are
accepted so an export from a spreadsheet usually works unedited.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .models import DealAgentError, Listing, ValidationError

# Statewide averages used only when a column is missing, so a bare
# price-and-rent file still produces realistic numbers.
DEFAULT_TAX_RATE = 0.0062
DEFAULT_INSURANCE_RATE = 0.0035

REQUIRED_FIELDS = ("id", "list_price", "monthly_rent")

FIELD_ALIASES: Mapping[str, str] = {
    "price": "list_price",
    "listprice": "list_price",
    "asking_price": "list_price",
    "rent": "monthly_rent",
    "market_rent": "monthly_rent",
    "estimated_rent": "monthly_rent",
    "zip": "zip_code",
    "postal_code": "zip_code",
    "taxes": "annual_taxes",
    "property_taxes": "annual_taxes",
    "insurance": "annual_insurance",
    "hoa": "monthly_hoa",
    "hoa_monthly": "monthly_hoa",
    "rehab": "rehab_cost",
    "repairs": "rehab_cost",
    "after_repair_value": "arv",
    "square_feet": "sqft",
    "sq_ft": "sqft",
}

FLOAT_FIELDS = (
    "list_price",
    "monthly_rent",
    "beds",
    "baths",
    "annual_taxes",
    "annual_insurance",
    "monthly_hoa",
    "rehab_cost",
    "arv",
)
INT_FIELDS = ("sqft", "year_built")
TEXT_FIELDS = ("id", "address", "city", "zip_code")


class ListingParseError(DealAgentError):
    """A row could not be turned into a :class:`~arizona_deal_agent.models.Listing`."""


def _normalize_key(key: str) -> str:
    cleaned = key.strip().lower().replace(" ", "_").replace("-", "_")
    return FIELD_ALIASES.get(cleaned, cleaned)


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def parse_number(value: Any, field: str, where: str) -> float:
    """Read a number that may arrive as ``$385,000`` or ``6.5%`` or ``385000``."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip().replace("$", "").replace(",", "").replace("_", "")
    percent = text.endswith("%")
    if percent:
        text = text[:-1]
    try:
        number = float(text)
    except ValueError as exc:
        raise ListingParseError(f"{where}: {field} is not a number (got {value!r})") from exc
    return number / 100 if percent else number


def record_to_listing(record: Mapping[str, Any], where: str = "record") -> Listing:
    """Build one listing from a mapping of raw column values."""
    normalized: dict[str, Any] = {}
    for raw_key, raw_value in record.items():
        if raw_key is None:
            continue
        key = _normalize_key(str(raw_key))
        if not _is_blank(raw_value):
            normalized[key] = raw_value

    missing = [field for field in REQUIRED_FIELDS if field not in normalized]
    if missing:
        raise ListingParseError(f"{where}: missing required field(s) {', '.join(missing)}")

    kwargs: dict[str, Any] = {}
    for field in TEXT_FIELDS:
        if field in normalized:
            kwargs[field] = str(normalized[field]).strip()
    for field in FLOAT_FIELDS:
        if field in normalized:
            kwargs[field] = parse_number(normalized[field], field, where)
    for field in INT_FIELDS:
        if field in normalized:
            kwargs[field] = int(parse_number(normalized[field], field, where))

    price = kwargs["list_price"]
    kwargs.setdefault("annual_taxes", round(price * DEFAULT_TAX_RATE, 2))
    kwargs.setdefault("annual_insurance", round(price * DEFAULT_INSURANCE_RATE, 2))

    try:
        return Listing(**kwargs)
    except ValidationError as exc:
        raise ListingParseError(f"{where}: {exc}") from exc
    except TypeError as exc:
        raise ListingParseError(f"{where}: {exc}") from exc


def load_csv(path: Path) -> list[Listing]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ListingParseError(f"{path}: file is empty")
        # Row 1 is the header, so data starts at row 2.
        return [
            record_to_listing(row, where=f"{path.name} row {number}")
            for number, row in enumerate(reader, start=2)
        ]


def load_json(path: Path) -> list[Listing]:
    with path.open(encoding="utf-8") as handle:
        try:
            payload = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ListingParseError(f"{path}: invalid JSON ({exc})") from exc

    if isinstance(payload, Mapping):
        payload = payload.get("listings", payload.get("results"))
    if not isinstance(payload, list):
        raise ListingParseError(f"{path}: expected a JSON array of listings")

    return [
        record_to_listing(item, where=f"{path.name} item {index}")
        for index, item in enumerate(payload)
    ]


def load_listings(path: str | Path) -> list[Listing]:
    """Load listings from a ``.csv`` or ``.json`` file."""
    resolved = Path(path)
    if not resolved.exists():
        raise ListingParseError(f"{resolved}: file not found")

    suffix = resolved.suffix.lower()
    if suffix == ".csv":
        listings = load_csv(resolved)
    elif suffix == ".json":
        listings = load_json(resolved)
    else:
        raise ListingParseError(f"{resolved}: unsupported file type '{suffix or 'none'}', use .csv or .json")

    duplicates = _duplicate_ids(listings)
    if duplicates:
        raise ListingParseError(f"{resolved}: duplicate listing id(s) {', '.join(sorted(duplicates))}")
    return listings


def _duplicate_ids(listings: Iterable[Listing]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for listing in listings:
        if listing.id in seen:
            duplicates.add(listing.id)
        seen.add(listing.id)
    return duplicates
