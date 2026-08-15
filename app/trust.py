"""Allowlisted sources and scam-signal filters for live listings.

The agent does not scrape the open web. Live rows must come from a host on
:data:`ALLOWED_HOSTS`. Titles that look like payment scams are dropped even
when the host is allowed. Official real-estate sites (Zillow, Redfin,
Realtor.com) are listed as lookup destinations only — we never fetch them.
"""

from __future__ import annotations

from urllib.parse import urlparse

from .models import Deal, LookupLink

# Hosts we will accept a listing URL from. Subdomains of these names are ok.
ALLOWED_HOSTS = frozenset(
    {
        "craigslist.org",
        "phoenix.craigslist.org",
        "ebay.com",
    }
)

# Public sites we will not scrape. The UI can send the user there to verify
# an address they already have from an allowlisted source.
LOOKUP_ONLY_HOSTS = (
    LookupLink(name="Zillow", url="https://www.zillow.com/"),
    LookupLink(name="Redfin", url="https://www.redfin.com/"),
    LookupLink(name="Realtor.com", url="https://www.realtor.com/"),
    LookupLink(name="Homes.com", url="https://www.homes.com/"),
    LookupLink(name="AZ Dept. of Real Estate", url="https://azre.gov/"),
)

# URL shorteners and disposable hosts that hide the real listing.
BLOCKED_HOSTS = frozenset(
    {
        "bit.ly",
        "tinyurl.com",
        "t.co",
        "goo.gl",
        "ow.ly",
        "is.gd",
        "cutt.ly",
    }
)

# Phrases that show up on gift-card / wire / crypto rental and for-sale scams.
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


def _parent_allowed(host: str) -> bool:
    if host in ALLOWED_HOSTS:
        return True
    return any(host.endswith(f".{allowed}") for allowed in ALLOWED_HOSTS if "." in allowed)


def is_allowlisted_url(url: str | None) -> bool:
    host = host_of(url)
    if host is None:
        return False
    if host in BLOCKED_HOSTS:
        return False
    return _parent_allowed(host)


def looks_like_scam(title: str) -> bool:
    text = title.lower()
    return any(phrase in text for phrase in SCAM_PHRASES)


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
        kept.append(deal.model_copy(update={"verified": True}))
    return kept
