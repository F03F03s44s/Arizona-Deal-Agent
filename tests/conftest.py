"""Shared test setup.

Tests never touch the network or the developer's saved-search file: the deal
service is pointed at fixed listings and the store at a temporary directory.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

# app.main reads both of these when it is imported, so they have to be set
# before any test module pulls it in.
os.environ["DEAL_AGENT_DATA_DIR"] = tempfile.mkdtemp(prefix="deal-agent-tests-")
os.environ["ALERT_POLL_SECONDS"] = "0"
os.environ.pop("SMTP_HOST", None)

import pytest  # noqa: E402

from app.craigslist import Listing, parse_search_payload  # noqa: E402
from app.deals import deal_service  # noqa: E402

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def make_listing(posting_id: str, title: str, price: float, **kwargs) -> Listing:
    return Listing(
        posting_id=posting_id,
        title=title,
        price=price,
        url=f"https://www.craigslist.org/view/d/slug/{posting_id}",
        location=kwargs.pop("location", "Tempe"),
        **kwargs,
    )


@pytest.fixture
def phoenix_payload() -> dict:
    """A trimmed copy of a real Craigslist JSON search response."""
    path = FIXTURE_DIR / "craigslist_phoenix_power_tools.json"
    return json.loads(path.read_text())


@pytest.fixture
def phoenix_listings(phoenix_payload: dict) -> list[Listing]:
    return parse_search_payload(phoenix_payload)


@pytest.fixture
def sample_listings() -> list[Listing]:
    """A cohort with hand-picked prices so comparables are predictable.

    The four drills are comparables for each other, the bargain drill is far
    under their median, and the saw shares no words with anything.
    """
    return [
        make_listing("drill-a", "DeWalt cordless drill", 200),
        make_listing("drill-b", "DeWalt cordless drill", 220),
        make_listing("drill-c", "DeWalt cordless drill", 240),
        make_listing("drill-d", "DeWalt cordless drill", 260),
        make_listing("bargain", "DeWalt cordless drill", 40, location="Mesa"),
        make_listing("saw", "Makita circular saw", 150),
    ]


@pytest.fixture(autouse=True)
def offline_deal_service(sample_listings: list[Listing], monkeypatch) -> list[tuple]:
    """Serve deals from fixed listings and record every scrape attempt."""
    calls: list[tuple] = []

    def fake_search(query: str, **kwargs):
        calls.append((query, kwargs))
        return sample_listings

    monkeypatch.setattr(deal_service, "searcher", fake_search)
    deal_service.invalidate()
    yield calls
    deal_service.invalidate()


@pytest.fixture(autouse=True)
def clean_store():
    from app.main import store

    store.clear()
    yield
    store.clear()
