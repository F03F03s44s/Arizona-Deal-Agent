"""Tests for the Phoenix Craigslist scraper."""

from pathlib import Path

from app.scraper import clear_scrape_cache, parse_search_html, scrape_phoenix_deals

FIXTURE = Path(__file__).parent / "fixtures" / "phoenix_search.html"


def test_parse_search_html_extracts_priced_deals():
    html = FIXTURE.read_text(encoding="utf-8")
    deals = parse_search_html(html, limit=10)
    assert len(deals) >= 3
    assert all(d.acquisition_cost > 0 for d in deals)
    assert all(d.market_value >= d.acquisition_cost for d in deals)
    assert all(d.source == "craigslist" for d in deals)
    assert any(d.url and "craigslist.org" in d.url for d in deals)


def test_furniture_gets_furniture_category():
    html = FIXTURE.read_text(encoding="utf-8")
    deals = parse_search_html(html)
    bed = next(d for d in deals if "Bed Frame" in d.title)
    assert bed.category == "furniture"
    assert bed.market_value > bed.acquisition_cost


def test_scrape_uses_injected_client(monkeypatch):
    clear_scrape_cache()
    html = FIXTURE.read_text(encoding="utf-8")

    class FakeResponse:
        text = html

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            return FakeResponse()

        def close(self):
            return None

    monkeypatch.setattr("app.scraper.httpx.Client", FakeClient)
    deals = scrape_phoenix_deals(refresh=True, limit=5)
    assert len(deals) == 5
    assert deals[0].source == "craigslist"
