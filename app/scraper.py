"""Phoenix-area Craigslist scraper for live deal inventory.

Fetches the public search results page, parses the no-JS static listing
markup Craigslist still embeds in the HTML, and converts each priced
posting into a ``Deal``. Asking price is treated as acquisition cost;
market value is estimated from category heuristics so the ranking engine
can surface underpriced flips.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from html import unescape
from typing import Iterable

import httpx
from bs4 import BeautifulSoup

from .models import Deal

logger = logging.getLogger(__name__)

PHOENIX_SEARCH_URL = "https://phoenix.craigslist.org/search/sss"
DEFAULT_MAX_PRICE = 25_000
DEFAULT_LIMIT = 60
CACHE_TTL_SECONDS = 10 * 60

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

# Expected resale multiplier by keyword category. Underpriced Craigslist
# asking prices often clear near these retail-ish levels.
CATEGORY_MARKUPS: list[tuple[str, str, float]] = [
    ("furniture", r"\b(sofa|couch|table|chair|desk|dresser|mattress|bed|sectional)\b", 1.75),
    ("electronics", r"\b(iphone|ipad|macbook|laptop|tv|ps5|xbox|nintendo|camera)\b", 1.35),
    ("tools", r"\b(dewalt|milwaukee|makita|table saw|drill|tool|compressor)\b", 1.65),
    ("auto", r"\b(toyota|honda|ford|chevy|truck|sedan|suv|car |tires?|rim)\b", 1.25),
    ("appliances", r"\b(fridge|refrigerator|washer|dryer|stove|oven|dishwasher)\b", 1.55),
    ("sports", r"\b(bike|bicycle|golf|kayak|treadmill|weights?)\b", 1.5),
    ("instruments", r"\b(guitar|piano|drum|violin|amp)\b", 1.55),
]

URGENCY_BONUS = re.compile(
    r"\b(must sell|moving|estate|as[- ]is|obo|make offer|priced to sell|firm)\b",
    re.I,
)
PRICE_RE = re.compile(r"[\d,]+(?:\.\d+)?")

_cache: dict[str, object] = {"fetched_at": 0.0, "deals": []}


def _classify(title: str) -> tuple[str, float]:
    lowered = title.lower()
    for category, pattern, markup in CATEGORY_MARKUPS:
        if re.search(pattern, lowered):
            return category, markup
    return "general", 1.4


def _estimate_market_value(title: str, asking_price: float) -> tuple[str, float]:
    category, markup = _classify(title)
    if URGENCY_BONUS.search(title):
        markup += 0.15
    # Soft-cap extreme markups on very cheap placeholder prices.
    if asking_price < 25:
        markup = min(markup, 1.2)
    return category, round(asking_price * markup, 2)


def _parse_price(text: str) -> float | None:
    if not text:
        return None
    match = PRICE_RE.search(text.replace(",", ""))
    if not match:
        return None
    try:
        value = float(match.group(0).replace(",", ""))
    except ValueError:
        return None
    if value <= 0:
        return None
    return value


def _stable_id(url: str, title: str) -> str:
    digest = hashlib.sha1(f"{url}|{title}".encode("utf-8")).hexdigest()[:12]
    return f"cl-{digest}"


def parse_search_html(html: str, *, limit: int = DEFAULT_LIMIT) -> list[Deal]:
    """Parse Craigslist static search HTML into Deal objects."""
    soup = BeautifulSoup(html, "lxml")
    deals: list[Deal] = []
    seen: set[str] = set()

    for item in soup.select("li.cl-static-search-result"):
        if len(deals) >= limit:
            break
        link = item.find("a", href=True)
        if link is None:
            continue
        title_el = item.select_one(".title")
        price_el = item.select_one(".price")
        location_el = item.select_one(".location")
        title = unescape((title_el.get_text(strip=True) if title_el else item.get("title") or "").strip())
        if not title:
            continue
        asking = _parse_price(price_el.get_text(" ", strip=True) if price_el else "")
        if asking is None:
            continue
        url = link["href"].strip()
        deal_id = _stable_id(url, title)
        if deal_id in seen:
            continue
        seen.add(deal_id)
        category, market_value = _estimate_market_value(title, asking)
        location = (location_el.get_text(" ", strip=True) if location_el else "").strip()
        deals.append(
            Deal(
                id=deal_id,
                title=title if not location else f"{title} ({location})",
                category=category,
                acquisition_cost=asking,
                market_value=max(market_value, asking),
                url=url,
                location=location or None,
                source="craigslist",
            )
        )
    return deals


def fetch_search_html(
    *,
    query: str | None = None,
    max_price: int = DEFAULT_MAX_PRICE,
    client: httpx.Client | None = None,
) -> str:
    """HTTP-fetch the Phoenix Craigslist for-sale search page."""
    params: dict[str, str | int] = {
        "max_price": max_price,
        "hasPic": 1,
        "bundleDuplicates": 1,
    }
    if query:
        params["query"] = query

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://phoenix.craigslist.org/",
    }

    owns_client = client is None
    http = client or httpx.Client(timeout=30.0, follow_redirects=True)
    try:
        response = http.get(PHOENIX_SEARCH_URL, params=params, headers=headers)
        response.raise_for_status()
        return response.text
    finally:
        if owns_client:
            http.close()


def scrape_phoenix_deals(
    *,
    query: str | None = None,
    max_price: int = DEFAULT_MAX_PRICE,
    limit: int = DEFAULT_LIMIT,
    refresh: bool = False,
    client: httpx.Client | None = None,
) -> list[Deal]:
    """Scrape Phoenix Craigslist deals, with a short in-memory cache."""
    now = time.time()
    cached_deals = _cache.get("deals") or []
    fetched_at = float(_cache.get("fetched_at") or 0.0)
    cache_key = f"{query or ''}|{max_price}|{limit}"
    if (
        not refresh
        and cached_deals
        and _cache.get("key") == cache_key
        and now - fetched_at < CACHE_TTL_SECONDS
    ):
        return list(cached_deals)  # type: ignore[arg-type]

    html = fetch_search_html(query=query, max_price=max_price, client=client)
    deals = parse_search_html(html, limit=limit)
    _cache["deals"] = deals
    _cache["fetched_at"] = now
    _cache["key"] = cache_key
    logger.info("Scraped %d Phoenix Craigslist deals", len(deals))
    return deals


def clear_scrape_cache() -> None:
    _cache["deals"] = []
    _cache["fetched_at"] = 0.0
    _cache["key"] = None


def deals_from_iterable(raw: Iterable[Deal]) -> list[Deal]:
    return list(raw)
