"""Load the curated Arizona house catalog as web deals.

These are the same listings the CLI ranks (`data/sample_listings.csv`). They
are treated as verified because they ship with the project; we do not scrape
Zillow or Redfin for them. Each row gets official-site lookup links so you
can confirm the address yourself.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from arizona_deal_agent.sources import load_listings

from .models import Deal, LookupLink
from .trust import filter_lookup_links

DEFAULT_CATALOG = Path(__file__).resolve().parents[1] / "data" / "sample_listings.csv"


def catalog_path() -> Path:
    override = os.getenv("DEAL_AGENT_CATALOG")
    return Path(override) if override else DEFAULT_CATALOG


def official_lookups(address: str, city: str, zip_code: str) -> list[LookupLink]:
    """Search pages on official sites — opened in the browser, never scraped."""
    city_slug = quote(city.replace(" ", "-")) if city else "Phoenix"
    full = " ".join(part for part in (address, city, "AZ", zip_code) if part)
    zillow_slug = quote(full.replace(" ", "-")) if full.strip() else city_slug
    query = quote(full) if full.strip() else quote(f"{city} AZ")
    links = [
        LookupLink(name="Zillow", url=f"https://www.zillow.com/homes/{zillow_slug}_rb/"),
        LookupLink(name="Redfin", url=f"https://www.redfin.com/AZ/{city_slug}"),
        LookupLink(name="Realtor.com", url=f"https://www.realtor.com/realestateandhomes-search/{city_slug}_AZ"),
        LookupLink(name="Google", url=f"https://www.google.com/search?q={query}"),
    ]
    return filter_lookup_links(links)


def _matches_query(listing, query: str) -> bool:
    needle = query.strip().lower()
    if not needle or needle in {"arizona house", "houses", "house", "property"}:
        return True
    haystack = " ".join(
        part.lower()
        for part in (listing.id, listing.address, listing.city, listing.zip_code)
        if part
    )
    return needle in haystack


def load_catalog_deals(query: str | None = None) -> list[Deal]:
    listings = load_listings(catalog_path())
    deals: list[Deal] = []
    for listing in listings:
        if query and not _matches_query(listing, query):
            continue
        market = listing.arv if listing.arv else listing.list_price
        title = listing.label
        beds = f"{listing.beds:g} bd / {listing.baths:g} ba" if listing.beds or listing.baths else ""
        if beds:
            title = f"{title} ({beds})"
        deals.append(
            Deal(
                id=f"cat-{listing.id}",
                title=title,
                category="property",
                acquisition_cost=listing.list_price,
                market_value=market,
                location=f"{listing.city}, AZ" if listing.city else "Arizona",
                source="verified-catalog",
                source_label="Arizona verified catalog",
                verified=True,
                comparable_count=0,
                lookup_urls=official_lookups(listing.address, listing.city, listing.zip_code),
            )
        )
    return deals
