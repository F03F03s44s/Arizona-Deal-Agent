"""Allowlisted sources and scam-signal filters for live listings.

Only hosts in :data:`ALLOWED_HOSTS` may appear as a live listing URL, and only
hosts in :data:`VERIFIED_LOOKUP_HOSTS` may appear as a "check it yourself"
link. Unknown, lookalike, and shortened URLs are dropped. A listing can still
be a bad seller — we verify the *site*, then filter obvious scam wording.
"""

from __future__ import annotations

from urllib.parse import urlparse

from .models import Deal, LookupLink, SourceInfo

# Hosts we will accept a listing URL from. Subdomains of these names are ok.
# Nothing else is fetched or shown as a live deal link.
ALLOWED_HOSTS = frozenset(
    {
        "craigslist.org",
        "ebay.com",
    }
)

# Official sites we will not scrape. The UI may link out so the buyer can
# confirm an address, a cert, or a comp. Random marketplaces are not added.
VERIFIED_LOOKUP_HOSTS = frozenset(
    {
        "zillow.com",
        "redfin.com",
        "realtor.com",
        "homes.com",
        "azre.gov",
        "kitco.com",
        "gia.edu",
        "stockx.com",
        "tcgplayer.com",
        "pcgs.com",
        "bstock.com",
        "ebay.com",
        "google.com",
    }
)

LOOKUP_ONLY_HOSTS = (
    LookupLink(name="Zillow", url="https://www.zillow.com/"),
    LookupLink(name="Redfin", url="https://www.redfin.com/"),
    LookupLink(name="Realtor.com", url="https://www.realtor.com/"),
    LookupLink(name="Homes.com", url="https://www.homes.com/"),
    LookupLink(name="AZ Dept. of Real Estate", url="https://azre.gov/"),
)

# URL shorteners, chat apps, and disposable hosts that hide the real listing.
BLOCKED_HOSTS = frozenset(
    {
        "bit.ly",
        "tinyurl.com",
        "t.co",
        "goo.gl",
        "ow.ly",
        "is.gd",
        "cutt.ly",
        "tiny.cc",
        "rebrand.ly",
        "shorturl.at",
        "rb.gy",
        "t.me",
        "telegram.me",
        "wa.me",
        "discord.gg",
        "paypal.me",
        "cash.app",
    }
)

# Phrases that show up on gift-card / wire / crypto / advance-fee scams.
SCAM_PHRASES = (
    "gift card",
    "giftcard",
    "western union",
    "moneygram",
    "money gram",
    "wire transfer",
    "wire the",
    "send bitcoin",
    "send crypto",
    "cryptocurrency",
    "cashier check",
    "cashier's check",
    "certified check",
    "google hangout",
    "overseas",
    "out of the country",
    "deployed",
    "military deployed",
    "send deposit",
    "deposit via",
    "pay with zelle only",
    "cash app",
    "cashapp",
    "friends and family",
    "holding fee",
    "booking fee",
    "advance fee",
    "pay the shipper",
    "shipping agent",
    "too good to be true",
    "act now send",
    "processing fee first",
    "replica",
    "1:1",
    "mirror quality",
    "aaa quality",
    "not authentic",
    "counterfeit",
    "proxy card",
    "fake psa",
)


def host_of(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _is_https(url: str) -> bool:
    return urlparse(url).scheme == "https"


def _host_matches(host: str, allowed: frozenset[str]) -> bool:
    if host in allowed:
        return True
    return any(host.endswith(f".{name}") for name in allowed)


def is_allowlisted_url(url: str | None) -> bool:
    """True only for https listing URLs on Craigslist or eBay."""
    if not url or not _is_https(url):
        return False
    host = host_of(url)
    if host is None or host in BLOCKED_HOSTS:
        return False
    return _host_matches(host, ALLOWED_HOSTS)


def is_verified_lookup_url(url: str | None) -> bool:
    """True only for https links to the official lookup allowlist."""
    if not url or not _is_https(url):
        return False
    host = host_of(url)
    if host is None or host in BLOCKED_HOSTS:
        return False
    return _host_matches(host, VERIFIED_LOOKUP_HOSTS)


def looks_like_scam(title: str) -> bool:
    text = title.lower()
    return any(phrase in text for phrase in SCAM_PHRASES)


def filter_lookup_links(links: list[LookupLink]) -> list[LookupLink]:
    return [link for link in links if is_verified_lookup_url(link.url)]


def is_safe_source_url(kind: str, url: str | None) -> bool:
    """True when a source card may show this URL."""
    if not url:
        return kind == "catalog"
    if kind == "live":
        return is_allowlisted_url(url)
    return is_verified_lookup_url(url)


def filter_source_infos(sources: list[SourceInfo]) -> list[SourceInfo]:
    """Keep only allowlisted source cards and mark them verified."""
    kept: list[SourceInfo] = []
    for source in sources:
        if not is_safe_source_url(source.kind, source.url):
            continue
        kept.append(source.model_copy(update={"verified": True}))
    return kept


def sanitize_request_deals(deals: list[Deal]) -> list[Deal]:
    """Strip unknown listing URLs and drop scam-worded titles from POSTed deals."""
    cleaned: list[Deal] = []
    for deal in deals:
        if looks_like_scam(deal.title):
            continue
        url = deal.url if is_allowlisted_url(deal.url) else None
        cleaned.append(
            deal.model_copy(
                update={
                    "url": url,
                    "lookup_urls": filter_lookup_links(deal.lookup_urls),
                    "verified": bool(url) or deal.source == "verified-catalog",
                }
            )
        )
    return cleaned


def filter_live_deals(deals: list[Deal]) -> list[Deal]:
    """Keep only allowlisted, non-scam live listings.

    Sample / catalog rows have no public URL and are not run through this.
    """
    kept: list[Deal] = []
    for deal in deals:
        if not is_allowlisted_url(deal.url):
            continue
        if looks_like_scam(deal.title):
            continue
        kept.append(
            deal.model_copy(
                update={
                    "verified": True,
                    "lookup_urls": filter_lookup_links(deal.lookup_urls),
                }
            )
        )
    return kept
