"""Live Arizona foreclosure candidates from HUD's public REO map service.

When FHA pays a claim on a foreclosed home the lender transfers the property to
HUD, which then resells it. HUD publishes that inventory through an open ArcGIS
feature service that needs no key. The feed carries the address and where the
property sits in HUD's disposition pipeline, but no price or rent, so these
listings depend on the market enrichment step to become scoreable.

Service: https://egis.hud.gov/arcgis/rest/services/cpdmaps/HudSfReo/MapServer/1
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..models import Listing
from .base import Source, SourceError, clean_text, http_get_json

SERVICE_URL = "https://egis.hud.gov/arcgis/rest/services/cpdmaps/HudSfReo/MapServer/1/query"

# HUD's disposition pipeline. Steps 1-5 are acquired but not yet for sale,
# step 6 is publicly listed, and anything above that is already spoken for.
STEP_LABELS = {
    1: "In HUD inventory",
    2: "In HUD inventory",
    3: "In HUD inventory",
    4: "Appraisal ordered",
    5: "Preparing to list",
    6: "Listed for sale",
    7: "Offer accepted",
    8: "Under contract",
    9: "Closing",
    10: "Sold",
}
LISTED_STEP = 6


class HudReoSource(Source):
    """HUD-owned single-family homes on the market or heading to market."""

    name = "hud-reo"
    description = "HUD FHA single-family foreclosures (live, egis.hud.gov)"
    is_live = True

    def __init__(
        self,
        state: str = "AZ",
        listed_only: bool = True,
        service_url: str = SERVICE_URL,
        timeout: float = 30.0,
    ) -> None:
        self.state = state.upper()
        self.listed_only = listed_only
        self.service_url = service_url
        self.timeout = timeout

    def _where(self) -> str:
        clauses = [f"STATE_CODE='{self.state}'", "DATE_CLOSED IS NULL"]
        clauses.append(
            f"CASE_STEP_NUMBER={LISTED_STEP}"
            if self.listed_only
            else f"CASE_STEP_NUMBER<={LISTED_STEP}"
        )
        return " AND ".join(clauses)

    def fetch(self, limit: int | None = None) -> list[Listing]:
        params = {
            "where": self._where(),
            "outFields": "*",
            "returnGeometry": "false",
            "orderByFields": "CASE_STEP_NUMBER DESC,DATE_ACQUIRED DESC",
            "f": "json",
        }
        if limit:
            params["resultRecordCount"] = str(limit)

        payload = http_get_json(self.service_url, params, timeout=self.timeout)
        if "error" in payload:
            message = payload["error"].get("message", "unknown error")
            raise SourceError(f"HUD REO service error: {message}")

        listings = [self._to_listing(f.get("attributes", {})) for f in payload.get("features", [])]
        return [listing for listing in listings if listing is not None]

    def _to_listing(self, row: dict) -> Listing | None:
        case_num = clean_text(row.get("CASE_NUM"))
        if not case_num:
            return None

        step = row.get("CASE_STEP_NUMBER")
        step = int(step) if isinstance(step, (int, float)) else None
        zip_code = row.get("DISPLAY_ZIP_CODE")
        zip_code = str(int(zip_code)).zfill(5) if isinstance(zip_code, (int, float)) else ""

        address = clean_text(row.get("ADDRESS")) or clean_text(
            f"{row.get('STREET_NUM') or ''} {row.get('DIRECTION_PREFIX') or ''} "
            f"{row.get('STREET_NAME') or ''}"
        )

        return Listing(
            id=f"HUD-{case_num}",
            source=self.name,
            address=address.title(),
            city=clean_text(row.get("CITY")).title(),
            state=clean_text(row.get("STATE_CODE")) or self.state,
            zip_code=zip_code,
            latitude=_as_float(row.get("MAP_LATITUDE")),
            longitude=_as_float(row.get("MAP_LONGITUDE")),
            status=STEP_LABELS.get(step or 0, "In HUD inventory"),
            url="https://www.hudhomestore.gov/searchresult?state=" + self.state,
            detail={
                "case_number": case_num,
                "case_step": step,
                "acquired": _as_date(row.get("DATE_ACQUIRED")),
                "county_fips": row.get("FIPS_STATE_CODE"),
            },
        )


def _as_float(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _as_date(value: object) -> str:
    """ArcGIS returns epoch milliseconds; render as an ISO date."""
    if not isinstance(value, (int, float)):
        return ""
    return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc).date().isoformat()
