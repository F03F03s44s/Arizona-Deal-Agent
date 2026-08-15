"""Arizona market values and rents, keyed by ZIP code.

Public feeds of distressed property publish an address but rarely a price or a
rent, so a bare address cannot be underwritten on its own. This module supplies
the missing side of the equation from Zillow's free research data: ZHVI for the
typical home value in a ZIP and ZORI for the typical asking rent.

A filtered Arizona snapshot ships with the package so the agent works offline
and scores deterministically. ``build_snapshot`` regenerates it from the live
files; ``scripts/refresh_market_data.py`` is the maintenance entry point.
"""

from __future__ import annotations

import csv
import io
import json
import statistics
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Iterator

SNAPSHOT_PATH = Path(__file__).parent / "data" / "az_market.json"

ZHVI_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zhvi/"
    "Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
)
ZORI_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zori/"
    "Zip_zori_uc_sfrcondomfr_sm_month.csv"
)

# Fallbacks for ZIPs the snapshot does not cover. Derived from the statewide
# medians of the same snapshot so an unknown ZIP lands in a plausible place
# instead of dropping out of the ranking.
DEFAULT_VALUE = 350_000.0
DEFAULT_RENT = 1_900.0


@dataclass(frozen=True)
class ZipMarket:
    """Typical home value and rent for one Arizona ZIP code."""

    zip_code: str
    city: str = ""
    county: str = ""
    metro: str = ""
    typical_value: float | None = None
    typical_rent: float | None = None

    @property
    def rent_to_value(self) -> float | None:
        if not self.typical_value or not self.typical_rent:
            return None
        return (self.typical_rent * 12.0) / self.typical_value


@dataclass(frozen=True)
class MarketData:
    """Snapshot of Arizona ZIP-level values and rents."""

    zips: dict[str, ZipMarket]
    cities: dict[str, ZipMarket]
    generated_at: str = ""
    value_as_of: str = ""
    rent_as_of: str = ""
    median_value: float = DEFAULT_VALUE
    median_rent: float = DEFAULT_RENT

    def lookup(self, zip_code: str = "", city: str = "") -> ZipMarket | None:
        """Best available market for a ZIP, falling back to the city median."""
        key = _clean_zip(zip_code)
        if key and key in self.zips:
            return self.zips[key]
        city_key = city.strip().lower()
        if city_key and city_key in self.cities:
            return self.cities[city_key]
        return None

    def statewide(self) -> ZipMarket:
        return ZipMarket(
            zip_code="",
            city="Arizona",
            typical_value=self.median_value,
            typical_rent=self.median_rent,
        )


def _clean_zip(value: object) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[:5].zfill(5) if digits else ""


def load_snapshot(path: str | Path | None = None) -> MarketData:
    """Load the packaged Arizona market snapshot (or one at ``path``)."""
    source = Path(path) if path else SNAPSHOT_PATH
    if not source.exists():
        return MarketData(zips={}, cities={})
    with source.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return from_payload(payload)


def from_payload(payload: dict) -> MarketData:
    zips: dict[str, ZipMarket] = {}
    for zip_code, row in (payload.get("zips") or {}).items():
        key = _clean_zip(zip_code)
        zips[key] = ZipMarket(
            zip_code=key,
            city=row.get("city", ""),
            county=row.get("county", ""),
            metro=row.get("metro", ""),
            typical_value=row.get("value"),
            typical_rent=row.get("rent"),
        )

    cities: dict[str, ZipMarket] = {}
    for name, row in (payload.get("cities") or {}).items():
        cities[name.strip().lower()] = ZipMarket(
            zip_code="",
            city=row.get("city", name),
            county=row.get("county", ""),
            metro=row.get("metro", ""),
            typical_value=row.get("value"),
            typical_rent=row.get("rent"),
        )

    values = [m.typical_value for m in zips.values() if m.typical_value]
    rents = [m.typical_rent for m in zips.values() if m.typical_rent]
    return MarketData(
        zips=zips,
        cities=cities,
        generated_at=payload.get("generated_at", ""),
        value_as_of=payload.get("value_as_of", ""),
        rent_as_of=payload.get("rent_as_of", ""),
        median_value=statistics.median(values) if values else DEFAULT_VALUE,
        median_rent=statistics.median(rents) if rents else DEFAULT_RENT,
    )


def _stream_csv(url: str, timeout: float = 180.0) -> Iterator[dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": "arizona-deal-agent/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        stream = io.TextIOWrapper(response, encoding="utf-8", newline="")
        yield from csv.DictReader(stream)


def _latest_month(row: dict[str, str], months: Iterable[str]) -> tuple[str, float] | None:
    for month in reversed(list(months)):
        raw = (row.get(month) or "").strip()
        if raw:
            try:
                return month, float(raw)
            except ValueError:
                continue
    return None


def _month_columns(fieldnames: Iterable[str]) -> list[str]:
    return [name for name in fieldnames if name[:4].isdigit() and "-" in name]


def build_snapshot(
    state: str = "AZ",
    zhvi_url: str = ZHVI_URL,
    zori_url: str = ZORI_URL,
    reader=_stream_csv,
) -> dict:
    """Download ZHVI and ZORI and reduce them to one state's latest figures."""
    zips: dict[str, dict] = {}
    value_as_of = ""
    rent_as_of = ""

    for row in reader(zhvi_url):
        if (row.get("State") or "").strip().upper() != state:
            continue
        months = _month_columns(row.keys())
        latest = _latest_month(row, months)
        if not latest:
            continue
        month, value = latest
        value_as_of = max(value_as_of, month)
        zips[_clean_zip(row.get("RegionName"))] = {
            "city": (row.get("City") or "").strip(),
            "county": (row.get("CountyName") or "").strip(),
            "metro": (row.get("Metro") or "").strip(),
            "value": round(value, 2),
        }

    for row in reader(zori_url):
        if (row.get("State") or "").strip().upper() != state:
            continue
        months = _month_columns(row.keys())
        latest = _latest_month(row, months)
        if not latest:
            continue
        month, rent = latest
        rent_as_of = max(rent_as_of, month)
        key = _clean_zip(row.get("RegionName"))
        entry = zips.setdefault(
            key,
            {
                "city": (row.get("City") or "").strip(),
                "county": (row.get("CountyName") or "").strip(),
                "metro": (row.get("Metro") or "").strip(),
            },
        )
        entry["rent"] = round(rent, 2)

    return {
        "generated_at": date.today().isoformat(),
        "state": state,
        "value_as_of": value_as_of,
        "rent_as_of": rent_as_of,
        "sources": [
            {"name": "Zillow Home Value Index (ZHVI), ZIP level", "url": zhvi_url},
            {"name": "Zillow Observed Rent Index (ZORI), ZIP level", "url": zori_url},
        ],
        "zips": dict(sorted(zips.items())),
        "cities": _city_medians(zips),
    }


def _city_medians(zips: dict[str, dict]) -> dict[str, dict]:
    """Aggregate ZIP rows into per-city medians used when a ZIP is unknown."""
    grouped: dict[str, list[dict]] = {}
    for row in zips.values():
        city = (row.get("city") or "").strip()
        if city:
            grouped.setdefault(city.lower(), []).append(row)

    cities: dict[str, dict] = {}
    for key, rows in sorted(grouped.items()):
        values = [r["value"] for r in rows if r.get("value")]
        rents = [r["rent"] for r in rows if r.get("rent")]
        entry: dict = {
            "city": rows[0].get("city", key.title()),
            "county": rows[0].get("county", ""),
            "metro": rows[0].get("metro", ""),
        }
        if values:
            entry["value"] = round(statistics.median(values), 2)
        if rents:
            entry["rent"] = round(statistics.median(rents), 2)
        cities[key] = entry
    return cities


def write_snapshot(payload: dict, path: str | Path | None = None) -> Path:
    target = Path(path) if path else SNAPSHOT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, sort_keys=False)
        handle.write("\n")
    return target
