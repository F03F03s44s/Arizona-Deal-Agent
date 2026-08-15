"""Scraper for Phoenix-area Craigslist listings.

Craigslist's search pages are a JavaScript app, and the legacy ``format=rss``
endpoint now answers 403, so the only usable source is the JSON search service
the site's own front end calls. It returns rows as position-encoded arrays
rather than objects, so :func:`parse_search_payload` does the decoding.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

SEARCH_URL = "https://sapi.craigslist.org/web/v8/postings/search/full"

# Craigslist area ids come from https://reference.craigslist.org/Areas.
PHOENIX_AREA_ID = 18
PHOENIX_HOSTNAME = "phoenix"

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


class CraigslistError(RuntimeError):
    """Raised when listings could not be fetched or understood."""


@dataclass(frozen=True)
class Listing:
    """One Craigslist "for sale" posting."""

    posting_id: str
    title: str
    price: float
    url: str
    location: str | None = None
    posted_at: datetime | None = None
    category_id: int | None = None


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

        title = row[-1]
        if not isinstance(title, str) or not title.strip():
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

        listings.append(
            Listing(
                posting_id=posting_id,
                title=title.strip(),
                price=float(price_raw),
                url=f"https://www.craigslist.org/view/d/{slug}/{hash_id}",
                location=_location_label(row, locations, slug, title),
                posted_at=posted_at,
                category_id=category,
            )
        )

    return listings


def search(
    query: str,
    *,
    area_id: int = PHOENIX_AREA_ID,
    limit: int = PAGE_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
    client: httpx.Client | None = None,
) -> list[Listing]:
    """Fetch "for sale" listings for ``query`` in one Craigslist area."""
    params = {
        "batch": f"{area_id}-0-{PAGE_SIZE}-0-0",
        "cc": "US",
        "lang": "en",
        "searchPath": "sss",
        "query": query,
    }
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    owns_client = client is None
    http = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        response = http.get(SEARCH_URL, params=params, headers=headers)
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
