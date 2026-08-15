"""Load listings from a CSV or JSON file you already have.

Column names are matched loosely so an MLS or agent export usually loads
without editing: ``price``/``list_price``, ``rent``/``monthly_rent``,
``arv``/``market_value`` and similar spellings all resolve to the same field,
and unknown columns are kept on ``Listing.detail`` rather than dropped.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from ..models import Listing
from .base import Source, SourceError, clean_text, parse_int, parse_money

ALIASES: dict[str, tuple[str, ...]] = {
    "id": ("id", "listing_id", "mls", "mls_id", "mls_number", "case_number", "parcel"),
    "address": ("address", "street", "street_address", "addr", "property_address"),
    "city": ("city", "town"),
    "state": ("state", "state_code"),
    "zip_code": ("zip_code", "zip", "zipcode", "postal_code", "postalcode"),
    "beds": ("beds", "bedrooms", "br", "bed"),
    "baths": ("baths", "bathrooms", "ba", "bath"),
    "sqft": ("sqft", "square_feet", "squarefeet", "living_area", "size"),
    "year_built": ("year_built", "yr_built", "yearbuilt", "built"),
    "latitude": ("latitude", "lat"),
    "longitude": ("longitude", "lon", "lng", "long"),
    "list_price": ("list_price", "price", "asking_price", "listprice", "list"),
    "monthly_rent": ("monthly_rent", "rent", "market_rent", "estimated_rent", "gross_rent"),
    "market_value": ("market_value", "arv", "after_repair_value", "estimated_value", "value"),
    "rehab_cost": ("rehab_cost", "rehab", "repairs", "repair_estimate", "renovation"),
    "annual_taxes": ("annual_taxes", "taxes", "property_taxes", "tax"),
    "annual_insurance": ("annual_insurance", "insurance", "hazard_insurance"),
    "monthly_hoa": ("monthly_hoa", "hoa", "hoa_fee", "hoa_dues"),
    "status": ("status", "listing_status"),
    "url": ("url", "link", "listing_url"),
}

MONEY_FIELDS = {
    "list_price",
    "monthly_rent",
    "market_value",
    "rehab_cost",
    "annual_taxes",
    "annual_insurance",
    "monthly_hoa",
}
NUMBER_FIELDS = {"beds", "baths", "sqft", "latitude", "longitude"}


def _normalise_key(key: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(key).strip().lower()).strip("_")


def _pick(row: dict[str, Any], field: str) -> Any:
    for alias in ALIASES[field]:
        if alias in row and row[alias] not in (None, ""):
            return row[alias]
    return None


class FileSource(Source):
    """Listings read from a local ``.csv`` or ``.json`` file."""

    is_live = False

    def __init__(self, path: str | Path, name: str | None = None) -> None:
        self.path = Path(path)
        self.name = name or f"file:{self.path.name}"
        self.description = f"Listings from {self.path}"

    def fetch(self, limit: int | None = None) -> list[Listing]:
        if not self.path.exists():
            raise SourceError(f"no such listings file: {self.path}")

        suffix = self.path.suffix.lower()
        if suffix == ".json":
            rows = self._read_json()
        elif suffix in {".csv", ".tsv", ".txt"}:
            rows = self._read_csv()
        else:
            raise SourceError(f"unsupported listings file type: {suffix or self.path.name}")

        listings = [self._to_listing(row, index) for index, row in enumerate(rows, start=1)]
        listings = [listing for listing in listings if listing is not None]
        return listings[:limit] if limit else listings

    def _read_csv(self) -> list[dict[str, Any]]:
        delimiter = "\t" if self.path.suffix.lower() == ".tsv" else ","
        with self.path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            if not reader.fieldnames:
                raise SourceError(f"{self.path} has no header row")
            return [{_normalise_key(k): v for k, v in row.items() if k} for row in reader]

    def _read_json(self) -> list[dict[str, Any]]:
        with self.path.open(encoding="utf-8") as handle:
            try:
                payload = json.load(handle)
            except json.JSONDecodeError as exc:
                raise SourceError(f"{self.path} is not valid JSON: {exc}") from exc

        if isinstance(payload, dict):
            for key in ("listings", "deals", "properties", "results", "data"):
                if isinstance(payload.get(key), list):
                    payload = payload[key]
                    break
            else:
                payload = [payload]
        if not isinstance(payload, list):
            raise SourceError(f"{self.path} does not contain a list of listings")
        return [{_normalise_key(k): v for k, v in row.items()} for row in payload]

    def _to_listing(self, row: dict[str, Any], index: int) -> Listing | None:
        values: dict[str, Any] = {}
        for field in ALIASES:
            raw = _pick(row, field)
            if raw is None:
                continue
            if field in MONEY_FIELDS or field in NUMBER_FIELDS:
                values[field] = parse_money(raw)
            elif field == "year_built":
                values[field] = parse_int(raw)
            else:
                values[field] = clean_text(raw)

        price = values.get("list_price")
        if price is None and values.get("monthly_rent") is None and not values.get("address"):
            return None

        known = set(sum(ALIASES.values(), ()))
        detail = {k: v for k, v in row.items() if k not in known and v not in (None, "")}

        return Listing(
            id=str(values.get("id") or f"{self.name}-{index:03d}"),
            source=self.name,
            address=values.get("address", ""),
            city=values.get("city", ""),
            state=values.get("state") or "AZ",
            zip_code=_zip(values.get("zip_code")),
            beds=values.get("beds"),
            baths=values.get("baths"),
            sqft=values.get("sqft"),
            year_built=values.get("year_built"),
            latitude=values.get("latitude"),
            longitude=values.get("longitude"),
            list_price=price,
            monthly_rent=values.get("monthly_rent"),
            market_value=values.get("market_value"),
            rehab_cost=values.get("rehab_cost") or 0.0,
            annual_taxes=values.get("annual_taxes"),
            annual_insurance=values.get("annual_insurance"),
            monthly_hoa=values.get("monthly_hoa") or 0.0,
            status=values.get("status", ""),
            url=values.get("url", ""),
            detail=detail,
        )


def _zip(value: object) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[:5].zfill(5) if digits else ""


def load_listings(path: str | Path, limit: int | None = None) -> Iterable[Listing]:
    """Convenience wrapper used by the public package API."""
    return FileSource(path).fetch(limit=limit)
