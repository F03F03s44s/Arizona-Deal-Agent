"""Tests for decoding Craigslist's JSON search responses."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from app import craigslist
from app.craigslist import CraigslistError, parse_search_payload, search


def test_parses_real_payload(phoenix_listings):
    # The fixture holds 11 rows, one of which is a $0 placeholder.
    assert len(phoenix_listings) == 10

    first = phoenix_listings[0]
    assert first.title == "10 piece Flex Power Tools Set"
    assert first.price == 500.0
    # Posting ids arrive as deltas from decode.minPostingId (7915878554).
    assert first.posting_id == "7946843218"
    assert first.url == (
        "https://www.craigslist.org/view/d/"
        "apache-junction-10-piece-flex-power/eeMN5hZjKAvFGN4qFKrDU8"
    )


def test_skips_listings_without_a_price(phoenix_listings):
    assert all(listing.price > 0 for listing in phoenix_listings)


def test_recovers_city_from_the_listing_slug(phoenix_listings):
    cities = {listing.location for listing in phoenix_listings}
    assert "Apache Junction" in cities
    assert "Scottsdale" in cities


def test_falls_back_to_the_subarea_when_the_slug_does_not_match(phoenix_listings):
    # "Hand&Power Tools..." slugifies differently on Craigslist's side, so the
    # city cannot be split off and the subarea label is used instead.
    by_title = {listing.title: listing for listing in phoenix_listings}
    assert by_title["Hand&Power Tools for the homeowner"].location == "North Phoenix"


def test_decodes_posting_timestamps(phoenix_listings):
    posted = phoenix_listings[0].posted_at
    assert posted is not None
    assert posted.tzinfo is not None
    assert posted > datetime(2026, 7, 16, tzinfo=UTC)


@pytest.mark.parametrize("payload", [{}, {"data": {}}, {"data": []}])
def test_rejects_unusable_payloads(payload):
    with pytest.raises(CraigslistError):
        parse_search_payload(payload)


def test_search_targets_the_phoenix_area(phoenix_payload):
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        seen["user-agent"] = request.headers["user-agent"]
        return httpx.Response(200, json=phoenix_payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    listings = search("power tools", limit=5, client=client)

    assert len(listings) == 5
    assert seen["query"] == "power tools"
    assert seen["searchPath"] == "sss"
    assert "Mozilla" in seen["user-agent"]
    # The service 400s on any page size other than its own, so a smaller limit
    # must be taken by trimming the response rather than asking for less.
    assert seen["batch"] == f"{craigslist.PHOENIX_AREA_ID}-0-{craigslist.PAGE_SIZE}-0-0"


def test_search_can_target_a_topic_section(phoenix_payload):
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return httpx.Response(200, json=phoenix_payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    search("sofa", search_path="fuo", limit=1, client=client)
    assert seen["searchPath"] == "fuo"


def test_search_rejects_an_unknown_section(phoenix_payload):
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=phoenix_payload)))
    with pytest.raises(CraigslistError, match="unsupported"):
        search("sofa", search_path="not-a-section", client=client)


def test_search_wraps_transport_failures():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(CraigslistError, match="request failed"):
        search("power tools", client=client)


def test_search_wraps_error_responses(phoenix_payload):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="blocked")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(CraigslistError):
        search("power tools", client=client)
