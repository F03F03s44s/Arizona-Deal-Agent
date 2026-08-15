"""Scraper for Phoenix-area Craigslist listings.

Craigslist's search pages are a JavaScript app, and the legacy ``format=rss``
endpoint now answers 403, so the only usable source is the JSON search service
the site's own front end calls. It returns rows as position-encoded arrays
rather than objects, so :func:`parse_search_payload` does the decoding.

Individual postings are a different story: those pages are server-rendered and
carry a schema.org JSON-LD block, which :func:`parse_detail_page` reads for the
description, location and photos instead of scraping markup.
"""

from __future__ import annotations

import html as html_lib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import httpx

from .categories import DEALER, DEFAULT_SEARCH_PATH, OWNER, describe

SEARCH_URL = "https://sapi.craigslist.org/web/v8/postings/search/full"

# Craigslist area ids come from https://reference.craigslist.org/Areas.
PHOENIX_AREA_ID = 18
PHOENIX_HOSTNAME = "phoenix"

# Every Arizona area Craigslist splits the state into.
AREAS: dict[int, str] = {
    18: "Phoenix",
    57: "Tucson",
    244: "Flagstaff / Sedona",
    419: "Prescott",
    370: "Yuma",
    468: "Sierra Vista",
    565: "Mohave County",
    651: "Show Low",
}

SUBAREA_LABELS = {
    "cph": "Central/South Phoenix",
    "evl": "East Valley",
    "nph": "North Phoenix",
    "wvl": "West Valley",
}

# Craigslist rejects non-browser clients on this endpoint, so identify as one.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 20.0

# The service only accepts this exact page size; anything else is a 400. Any
# smaller result set has to be taken by trimming the response.
PAGE_SIZE = 360

# Positions within each encoded row.
_IDX_POSTING_DELTA = 0
_IDX_DATE_DELTA = 1
_IDX_CATEGORY = 2
_IDX_PRICE = 3
_IDX_LOCATION = 4

# Leading tag of each variable-length group appended to a row.
_GROUP_HASH_ID = 13
_GROUP_SLUG = 6
_GROUP_HOUSING = 5  # [5, bedrooms, square feet] on housing rows


class CraigslistError(RuntimeError):
    """Raised when listings could not be fetched or understood."""


class ListingStatus(str, Enum):
    """Whether a posting is still up on Craigslist."""

    ACTIVE = "active"
    REMOVED = "removed"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Listing:
    """One Craigslist "for sale" or housing posting."""

    posting_id: str
    title: str
    price: float
    url: str
    location: str | None = None
    posted_at: datetime | None = None
    category_id: int | None = None
    bedrooms: int | None = None
    area_sqft: int | None = None

    @property
    def category_label(self) -> str | None:
        category = describe(self.category_id)
        return category.label if category else None

    @property
    def seller_type(self) -> str | None:
        """``owner`` or ``dealer``, from the category the seller posted under."""
        category = describe(self.category_id)
        return category.seller_type if category else None

    @property
    def is_property(self) -> bool:
        category = describe(self.category_id)
        return bool(category and category.is_property)


@dataclass(frozen=True)
class ListingDetail:
    """Everything the posting page says about one listing."""

    posting_id: str
    url: str
    title: str
    status: ListingStatus
    price: float | None = None
    description: str = ""
    images: list[str] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    map_url: str | None = None
    posted_at: datetime | None = None
    updated_at: datetime | None = None
    category_label: str | None = None
    seller_type: str | None = None
    # Contact details the seller chose to publish in the posting text.
    # Craigslist's own reply flow is behind /reply, which its robots.txt
    # disallows, so it is linked rather than scraped.
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    reply_url: str | None = None
    other_listings_url: str | None = None


def _group(row: list[Any], tag: int) -> list[Any] | None:
    for element in row:
        if isinstance(element, list) and element and element[0] == tag:
            return element
    return None


def _slugify(text: str) -> list[str]:
    cleaned = "".join(char.lower() if char.isalnum() else " " for char in text)
    return cleaned.split()


def _city_from_slug(slug: str, title: str) -> str | None:
    """Recover the city that Craigslist prefixed onto the listing slug.

    The slug is ``<city>-<truncated title>``, with no delimiter between the two,
    so the city is whatever remains once a run of slug words that starts the
    title is stripped off the end.
    """
    slug_words = slug.split("-")
    title_words = _slugify(title)
    if not slug_words or not title_words:
        return None

    for start in range(len(slug_words)):
        tail = slug_words[start:]
        if tail and tail == title_words[: len(tail)]:
            city_words = slug_words[:start]
            if city_words:
                return " ".join(word.capitalize() for word in city_words)
            return None
    return None


def _location_label(row: list[Any], locations: list[Any], slug: str, title: str) -> str | None:
    city = _city_from_slug(slug, title)
    if city:
        return city

    raw = row[_IDX_LOCATION] if len(row) > _IDX_LOCATION else None
    if not isinstance(raw, str) or ":" not in raw:
        return None
    try:
        index = int(raw.split(":", 1)[0])
    except ValueError:
        return None
    if not 0 <= index < len(locations):
        return None
    entry = locations[index]
    if not isinstance(entry, list) or len(entry) < 3:
        return None
    return SUBAREA_LABELS.get(entry[2], entry[2])


def _title_from_row(row: list[Any]) -> str | None:
    """Pull the title out of a search row.

    It is normally the last element, but housing rows append a bedrooms/square
    feet group after it, so the title is the last free-standing string that is
    not one of the fixed leading fields.
    """
    for index in range(len(row) - 1, _IDX_LOCATION + 1, -1):
        value = row[index]
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def parse_search_payload(payload: dict[str, Any]) -> list[Listing]:
    """Decode the JSON search service's position-encoded rows into listings."""
    data = payload.get("data")
    if not isinstance(data, dict):
        raise CraigslistError("Craigslist response had no data section")

    rows = data.get("items")
    if not isinstance(rows, list):
        raise CraigslistError("Craigslist response had no items")

    decode = data.get("decode") or {}
    # Posting ids and timestamps are sent as deltas from a shared base.
    min_posting_id = int(decode.get("minPostingId") or 0)
    min_date = int(decode.get("minDate") or 0)
    locations = decode.get("locations") or []

    listings: list[Listing] = []
    for row in rows:
        if not isinstance(row, list) or len(row) <= _IDX_LOCATION:
            continue

        title = _title_from_row(row)
        if title is None:
            continue

        price_raw = row[_IDX_PRICE]
        if not isinstance(price_raw, (int, float)) or price_raw <= 0:
            continue

        slug_group = _group(row, _GROUP_SLUG)
        hash_group = _group(row, _GROUP_HASH_ID)
        if not slug_group or len(slug_group) < 2 or not hash_group or len(hash_group) < 2:
            continue
        slug = str(slug_group[1])
        hash_id = str(hash_group[1])

        posting_delta = row[_IDX_POSTING_DELTA]
        posting_id = str(min_posting_id + int(posting_delta)) if isinstance(posting_delta, int) else hash_id

        posted_at = None
        date_delta = row[_IDX_DATE_DELTA]
        if min_date and isinstance(date_delta, int):
            posted_at = datetime.fromtimestamp(min_date + date_delta, tz=UTC)

        category = row[_IDX_CATEGORY] if isinstance(row[_IDX_CATEGORY], int) else None

        bedrooms = area_sqft = None
        housing = _group(row, _GROUP_HOUSING)
        if housing and len(housing) >= 3:
            bedrooms = housing[1] if isinstance(housing[1], int) and housing[1] > 0 else None
            area_sqft = housing[2] if isinstance(housing[2], int) and housing[2] > 0 else None

        listings.append(
            Listing(
                posting_id=posting_id,
                title=title,
                price=float(price_raw),
                url=f"https://www.craigslist.org/view/d/{slug}/{hash_id}",
                location=_location_label(row, locations, slug, title),
                posted_at=posted_at,
                category_id=category,
                bedrooms=bedrooms,
                area_sqft=area_sqft,
            )
        )

    return listings


def search(
    query: str = "",
    *,
    area_id: int = PHOENIX_AREA_ID,
    category: str = DEFAULT_SEARCH_PATH,
    seller_type: str | None = None,
    limit: int = PAGE_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
    client: httpx.Client | None = None,
) -> list[Listing]:
    """Fetch listings for ``query`` in one Craigslist area.

    ``category`` is a Craigslist search path (``sss`` for everything for sale,
    ``rea`` for real estate). ``seller_type`` narrows to ``owner`` or
    ``dealer``, the latter being the businesses and wholesalers.
    """
    params = {
        "batch": f"{area_id}-0-{PAGE_SIZE}-0-0",
        "cc": "US",
        "lang": "en",
        "searchPath": category or DEFAULT_SEARCH_PATH,
    }
    if query:
        params["query"] = query
    if seller_type in {OWNER, DEALER}:
        params["purveyor"] = seller_type

    owns_client = client is None
    http = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        response = http.get(SEARCH_URL, params=params, headers=_json_headers())
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        raise CraigslistError(f"Craigslist request failed: {exc}") from exc
    except ValueError as exc:
        raise CraigslistError(f"Craigslist returned invalid JSON: {exc}") from exc
    finally:
        if owns_client:
            http.close()

    return parse_search_payload(payload)[:limit]


def _json_headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT, "Accept": "application/json"}


def _page_headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT, "Accept": "text/html"}


_LD_POSTING_RE = re.compile(
    r'<script[^>]*id="ld_posting_data"[^>]*>(.*?)</script>', re.S
)
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
_ATTR_RE = re.compile(r'<div class="attr ([^"]+)">(.*?)</div>', re.S)
_LABEL_RE = re.compile(r'<span class="labl">(.*?)</span>', re.S)
_VALUE_RE = re.compile(r'<span class="valu">(.*?)</span>', re.S)
_POSTING_INFO_RE = re.compile(r'<p class="postinginfo[^"]*">(.*?)</p>', re.S)
_TIME_RE = re.compile(r'datetime="([^"]+)"')
_REPLY_RE = re.compile(r'data-href="(https://[^"]*?/reply/[^"]*?)"')
_OTHER_ADS_RE = re.compile(r'href="([^"]*userpostingid=[^"]*)"')
_TAG_RE = re.compile(r"<[^>]+>")

_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?1[\s.\-]?)?\(?([2-9]\d{2})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})(?!\d)"
)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}")

# Craigslist serves these with HTTP 200, so the body has to be inspected.
_REMOVED_MARKERS = ("this posting has been deleted", "this posting has been flagged")
_EXPIRED_MARKERS = ("this posting has expired",)


def _strip_tags(fragment: str) -> str:
    return " ".join(html_lib.unescape(_TAG_RE.sub(" ", fragment)).split())


def _parse_status(status_code: int, body: str) -> ListingStatus:
    if status_code == 404:
        return ListingStatus.REMOVED
    if status_code != 200:
        return ListingStatus.UNKNOWN

    lowered = body[:20000].lower()
    if any(marker in lowered for marker in _REMOVED_MARKERS):
        return ListingStatus.REMOVED
    if any(marker in lowered for marker in _EXPIRED_MARKERS):
        return ListingStatus.EXPIRED
    return ListingStatus.ACTIVE


def _parse_title_tag(body: str) -> tuple[str | None, str | None]:
    """Read category and seller type out of the page title.

    Titles read ``<name> - <category> - by owner - sale - craigslist``.
    """
    match = _TITLE_RE.search(body)
    if not match:
        return None, None
    parts = [part.strip() for part in html_lib.unescape(match.group(1)).split(" - ")]

    seller_type = None
    for part in parts:
        if part == "by owner":
            seller_type = OWNER
        elif part == "by dealer" or part == "by broker":
            seller_type = DEALER

    category = None
    if len(parts) >= 2 and parts[1] not in {"craigslist", "sale"}:
        category = parts[1]
    return category, seller_type


def _parse_attributes(body: str) -> dict[str, str]:
    attributes: dict[str, str] = {}
    for name, fragment in _ATTR_RE.findall(body):
        label_match = _LABEL_RE.search(fragment)
        value_match = _VALUE_RE.search(fragment)
        value = _strip_tags(value_match.group(1)) if value_match else ""
        if not value:
            continue
        if label_match:
            key = _strip_tags(label_match.group(1)).rstrip(":")
        else:
            # Flags such as "delivery available" carry no label of their own.
            key = name.replace("_", " ").strip()
        attributes[key or name] = value
    return attributes


def _parse_timestamps(body: str) -> tuple[datetime | None, datetime | None]:
    posted = updated = None
    for fragment in _POSTING_INFO_RE.findall(body):
        time_match = _TIME_RE.search(fragment)
        if not time_match:
            continue
        try:
            moment = datetime.fromisoformat(time_match.group(1))
        except ValueError:
            continue
        text = _strip_tags(fragment).lower()
        if text.startswith("updated"):
            updated = moment
        elif text.startswith("posted"):
            posted = moment
    return posted, updated


def _find_contacts(text: str) -> tuple[list[str], list[str]]:
    """Contact details the seller typed into the posting themselves."""
    phones = []
    for match in _PHONE_RE.finditer(text):
        formatted = f"({match.group(1)}) {match.group(2)}-{match.group(3)}"
        if formatted not in phones:
            phones.append(formatted)
    emails = list(dict.fromkeys(_EMAIL_RE.findall(text)))
    return phones[:5], emails[:5]


def parse_detail_page(body: str, url: str, status_code: int = 200) -> ListingDetail:
    """Read one posting page into a :class:`ListingDetail`.

    The page carries a schema.org JSON-LD block, which is used in preference to
    the surrounding markup wherever it has the field.
    """
    status = _parse_status(status_code, body)
    posting_id = url.rstrip("/").rsplit("/", 1)[-1]

    if status is not ListingStatus.ACTIVE:
        return ListingDetail(posting_id=posting_id, url=url, title="", status=status)

    posting: dict[str, Any] = {}
    ld_match = _LD_POSTING_RE.search(body)
    if ld_match:
        try:
            parsed = json.loads(ld_match.group(1))
            if isinstance(parsed, dict):
                posting = parsed
        except json.JSONDecodeError:
            posting = {}

    offers = posting.get("offers") if isinstance(posting.get("offers"), dict) else {}
    place = offers.get("availableAtOrFrom") if isinstance(offers.get("availableAtOrFrom"), dict) else {}
    geo = place.get("geo") if isinstance(place.get("geo"), dict) else {}
    postal = place.get("address") if isinstance(place.get("address"), dict) else {}

    def _float(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    latitude = _float(geo.get("latitude"))
    longitude = _float(geo.get("longitude"))

    address = ", ".join(
        part
        for part in (
            str(postal.get("streetAddress") or "").strip(),
            str(postal.get("addressLocality") or "").strip(),
            str(postal.get("addressRegion") or "").strip(),
            str(postal.get("postalCode") or "").strip(),
        )
        if part
    ) or None

    description = html_lib.unescape(str(posting.get("description") or "")).strip()
    category, seller_type = _parse_title_tag(body)
    posted_at, updated_at = _parse_timestamps(body)
    phones, emails = _find_contacts(description)

    reply_match = _REPLY_RE.search(body)
    reply_url = reply_match.group(1).replace("/__SERVICE_ID__", "") if reply_match else None
    other_match = _OTHER_ADS_RE.search(body)
    other_url = html_lib.unescape(other_match.group(1)) if other_match else None

    images = [str(src) for src in (posting.get("image") or []) if isinstance(src, str)]

    return ListingDetail(
        posting_id=posting_id,
        url=url,
        title=str(posting.get("name") or "").strip(),
        status=status,
        price=_float(offers.get("price")),
        description=description,
        images=images,
        attributes=_parse_attributes(body),
        address=address,
        latitude=latitude,
        longitude=longitude,
        map_url=(
            f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
            if latitude is not None and longitude is not None
            else None
        ),
        posted_at=posted_at,
        updated_at=updated_at,
        category_label=category,
        seller_type=seller_type,
        phones=phones,
        emails=emails,
        reply_url=reply_url,
        other_listings_url=other_url,
    )


def fetch_detail(
    url: str, *, timeout: float = DEFAULT_TIMEOUT, client: httpx.Client | None = None
) -> ListingDetail:
    """Fetch and parse one posting page."""
    owns_client = client is None
    http = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        response = http.get(url, headers=_page_headers())
    except httpx.HTTPError as exc:
        raise CraigslistError(f"Could not open listing: {exc}") from exc
    finally:
        if owns_client:
            http.close()

    return parse_detail_page(response.text, url, response.status_code)


def check_status(
    url: str, *, timeout: float = DEFAULT_TIMEOUT, client: httpx.Client | None = None
) -> ListingStatus:
    """Ask Craigslist whether a posting is still up."""
    owns_client = client is None
    http = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        response = http.get(url, headers=_page_headers())
    except httpx.HTTPError:
        return ListingStatus.UNKNOWN
    finally:
        if owns_client:
            http.close()

    return _parse_status(response.status_code, response.text)
