"""Official eBay Browse API client.

eBay listings are only fetched when ``EBAY_OAUTH_TOKEN`` is set. We do not
scrape ebay.com HTML. Without a token the agent still builds official search
URLs so you can open eBay yourself.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus

import httpx

from .craigslist import Listing

BROWSE_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
DEFAULT_LIMIT = 50
DEFAULT_TIMEOUT = 20.0


class EbayError(RuntimeError):
    """Raised when the official eBay API could not be used."""


@dataclass(frozen=True)
class EbayItem:
    item_id: str
    title: str
    price: float
    url: str
    location: str | None = None


def search_url(query: str) -> str:
    """Official eBay search page (Buy It Now) for a query."""
    return f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}&LH_BIN=1"


def _location(item: dict[str, Any]) -> str | None:
    loc = item.get("itemLocation") or {}
    city = loc.get("city")
    state = loc.get("stateOrProvince")
    parts = [part for part in (city, state) if part]
    return ", ".join(parts) if parts else None


def _price(item: dict[str, Any]) -> float | None:
    raw = (item.get("price") or {}).get("value")
    try:
        price = float(raw)
    except (TypeError, ValueError):
        return None
    return price if price > 0 else None


def parse_search_payload(payload: dict[str, Any]) -> list[Listing]:
    """Turn a Browse API search body into the same Listing shape Craigslist uses."""
    rows = payload.get("itemSummaries")
    if not isinstance(rows, list):
        return []

    listings: list[Listing] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        url = item.get("itemWebUrl")
        item_id = item.get("itemId")
        price = _price(item)
        if not title or not url or not item_id or price is None:
            continue
        listings.append(
            Listing(
                posting_id=str(item_id).replace("|", "-"),
                title=str(title).strip(),
                price=price,
                url=str(url),
                location=_location(item),
            )
        )
    return listings


def search(
    query: str,
    *,
    limit: int = DEFAULT_LIMIT,
    timeout: float = DEFAULT_TIMEOUT,
    token: str | None = None,
    client: httpx.Client | None = None,
) -> list[Listing]:
    """Search eBay via the official Browse API.

    Returns an empty list when no OAuth token is configured so tests and
    local installs never hit eBay unless the operator opted in.
    """
    oauth = token if token is not None else os.getenv("EBAY_OAUTH_TOKEN", "").strip()
    if not oauth:
        return []

    params = {"q": query, "limit": str(min(limit, 200))}
    headers = {
        "Authorization": f"Bearer {oauth}",
        "Accept": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
    }

    owns_client = client is None
    http = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        response = http.get(BROWSE_URL, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        raise EbayError(f"eBay request failed: {exc}") from exc
    except ValueError as exc:
        raise EbayError(f"eBay returned invalid JSON: {exc}") from exc
    finally:
        if owns_client:
            http.close()

    if not isinstance(payload, dict):
        raise EbayError("eBay returned an unexpected payload")
    return parse_search_payload(payload)[:limit]
