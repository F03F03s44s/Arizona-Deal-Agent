"""Official eBay Browse API client — never hits the network."""

import httpx
import pytest

from app.ebay import EbayError, parse_search_payload, search, search_url
from app.deals import DealService
from app.craigslist import Listing
from tests.web.conftest import make_listing


def test_search_url_is_an_official_ebay_page():
    url = search_url("pokemon cards")
    assert url.startswith("https://www.ebay.com/sch/i.html")
    assert "pokemon" in url


def test_search_without_a_token_does_not_call_ebay():
    called = []

    def handler(request: httpx.Request) -> httpx.Response:
        called.append(str(request.url))
        return httpx.Response(200, json={"itemSummaries": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert search("jersey", token="", client=client) == []
    assert called == []


def test_search_uses_the_official_browse_api(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={
                "itemSummaries": [
                    {
                        "itemId": "v1|111|0",
                        "title": "Charizard PSA 10",
                        "price": {"value": "80.00", "currency": "USD"},
                        "itemWebUrl": "https://www.ebay.com/itm/111",
                        "itemLocation": {"city": "Phoenix", "stateOrProvince": "AZ"},
                    },
                    {
                        "itemId": "v1|222|0",
                        "title": "Charizard PSA 9",
                        "price": {"value": "60.00", "currency": "USD"},
                        "itemWebUrl": "https://www.ebay.com/itm/222",
                    },
                    {
                        "itemId": "v1|333|0",
                        "title": "Charizard holo",
                        "price": {"value": "70.00", "currency": "USD"},
                        "itemWebUrl": "https://www.ebay.com/itm/333",
                    },
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    listings = search("charizard", token="test-token", client=client, limit=10)
    assert len(listings) == 3
    assert listings[0].url.startswith("https://www.ebay.com/itm/")
    assert "api.ebay.com/buy/browse" in seen["url"]
    assert seen["auth"] == "Bearer test-token"


def test_parse_skips_items_without_a_price():
    listings = parse_search_payload(
        {
            "itemSummaries": [
                {"itemId": "x", "title": "no price", "itemWebUrl": "https://www.ebay.com/itm/x"},
            ]
        }
    )
    assert listings == []


def test_search_wraps_http_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="nope")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(EbayError):
        search("gold", token="bad", client=client)


def test_deal_service_merges_ebay_results_on_a_goods_topic():
    def cl_search(query, **kwargs):
        return [
            make_listing("1", "Nike jersey", 80),
            make_listing("2", "Nike jersey", 90),
            make_listing("3", "Nike jersey", 100),
        ]

    def eb_search(query, **kwargs):
        return [
            Listing(
                posting_id="eb1",
                title="Nike jersey stitched",
                price=70,
                url="https://www.ebay.com/itm/eb1",
            ),
            Listing(
                posting_id="eb2",
                title="Nike jersey stitched",
                price=85,
                url="https://www.ebay.com/itm/eb2",
            ),
            Listing(
                posting_id="eb3",
                title="Nike jersey stitched",
                price=95,
                url="https://www.ebay.com/itm/eb3",
            ),
        ]

    sourced = DealService(searcher=cl_search, ebay_searcher=eb_search).get_deals(
        "jersey", topic="jerseys"
    )
    assert "craigslist" in sourced.source
    assert "ebay" in sourced.source
    assert sourced.fetched_at is not None
    ids = {deal.id for deal in sourced.deals}
    assert any(deal_id.startswith("eb-") for deal_id in ids)
    assert any(deal_id.startswith("cl-") for deal_id in ids)
    assert any(link.name == "eBay" for deal in sourced.deals for link in deal.lookup_urls)
