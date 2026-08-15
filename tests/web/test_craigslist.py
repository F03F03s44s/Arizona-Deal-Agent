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


def test_decodes_posting_timestamps(phoenix_payload, phoenix_listings):
    posted = phoenix_listings[0].posted_at
    assert posted is not None
    assert posted.tzinfo is not None

    # Timestamps are deltas from minPostedDate, so every one has to land in
    # the window the response declares. "minDate" is a different field about a
    # year ahead, and using it as the base dates every listing to next year.
    decode = phoenix_payload["data"]["decode"]
    oldest = datetime.fromtimestamp(decode["minPostedDate"], tz=UTC)
    newest = datetime.fromtimestamp(decode["maxPostedDate"], tz=UTC)
    assert all(oldest <= listing.posted_at <= newest for listing in phoenix_listings)
    assert decode["minDate"] != decode["minPostedDate"]


def test_listings_are_never_dated_in_the_future(phoenix_listings, real_estate_payload):
    now = datetime.now(UTC)
    for listing in phoenix_listings + parse_search_payload(real_estate_payload):
        assert listing.posted_at <= now


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


def test_search_passes_category_and_seller_type(phoenix_payload):
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return httpx.Response(200, json=phoenix_payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    search("", category="rea", seller_type="dealer", area_id=57, client=client)

    assert seen["searchPath"] == "rea"
    assert seen["purveyor"] == "dealer"
    assert seen["batch"].startswith("57-0-")
    # An empty query must not be sent as a filter at all.
    assert "query" not in seen


def test_seller_type_and_category_come_from_the_category_id(phoenix_listings):
    listing = phoenix_listings[0]
    assert listing.category_label == "tools"
    assert listing.seller_type == "owner"


# -- housing rows ---------------------------------------------------------


def test_housing_rows_keep_their_title(real_estate_payload):
    listings = parse_search_payload(real_estate_payload)

    # Housing rows put a bedrooms/sqft group after the title, so "the title is
    # the last element" does not hold for them. The fixture holds 7 rows, one
    # of which has no price.
    assert len(listings) == 6
    assert all(listing.title for listing in listings)
    assert "Three bedroom two bath swimming pool" in {l.title for l in listings}


def test_unpriced_property_listings_are_dropped(real_estate_payload):
    # Housing uses -1 rather than 0 to mean "no price given", and an unpriced
    # listing cannot be scored against comparables.
    assert any(row[3] == -1 for row in real_estate_payload["data"]["items"])
    assert all(listing.price > 0 for listing in parse_search_payload(real_estate_payload))


def test_housing_rows_carry_bedrooms_and_area(real_estate_payload):
    listings = parse_search_payload(real_estate_payload)
    with_beds = [listing for listing in listings if listing.bedrooms]

    assert with_beds
    assert all(listing.bedrooms > 0 for listing in with_beds)


def test_broker_listings_count_as_dealers(real_estate_payload):
    listings = parse_search_payload(real_estate_payload)
    seller_types = {listing.seller_type for listing in listings}

    assert seller_types <= {"owner", "dealer", None}
    assert all(listing.category_label == "real estate" for listing in listings)


# -- posting detail -------------------------------------------------------

DETAIL_URL = (
    "https://www.craigslist.org/view/d/"
    "apache-junction-10-piece-flex-power/eeMN5hZjKAvFGN4qFKrDU8"
)


def test_detail_reads_the_json_ld_block(listing_page):
    detail = craigslist.parse_detail_page(listing_page, DETAIL_URL)

    assert detail.status is craigslist.ListingStatus.ACTIVE
    assert detail.title == "10 piece Flex Power Tools Set"
    assert detail.price == 500.0
    assert "Impact driver" in detail.description
    assert len(detail.images) == 10


def test_detail_says_where_to_go(listing_page):
    detail = craigslist.parse_detail_page(listing_page, DETAIL_URL)

    assert detail.address == "Apache Junction, AZ, 85178"
    assert detail.latitude == pytest.approx(33.436645)
    assert detail.longitude == pytest.approx(-111.564161)
    assert detail.map_url is not None
    assert "33.436645,-111.564161" in detail.map_url


def test_detail_links_the_reply_flow_rather_than_scraping_it(listing_page):
    detail = craigslist.parse_detail_page(listing_page, DETAIL_URL)

    # Craigslist's robots.txt disallows /reply, so the URL is surfaced for the
    # human to click and never fetched.
    assert detail.reply_url == "https://phoenix.craigslist.org/reply/phx/tls/7946843218"
    assert "__SERVICE_ID__" not in detail.reply_url
    assert detail.other_listings_url is not None
    assert "userpostingid=7946843218" in detail.other_listings_url


def test_detail_collects_attributes_and_timestamps(listing_page):
    detail = craigslist.parse_detail_page(listing_page, DETAIL_URL)

    assert detail.attributes["condition"] == "excellent"
    assert "delivery available" in detail.attributes
    assert detail.category_label == "tools"
    assert detail.seller_type == "owner"
    assert detail.posted_at is not None
    assert detail.updated_at is not None
    assert detail.updated_at >= detail.posted_at


def test_detail_picks_up_contacts_the_seller_published():
    body = """
    <script type="application/ld+json" id="ld_posting_data" >
    {"name":"Tool lot","description":"Call 480-555-0134 or email me@example.com",
     "offers":{"price":"100"}}
    </script><title>Tool lot - tools - by dealer - sale - craigslist</title>
    """
    detail = craigslist.parse_detail_page(body, DETAIL_URL)

    assert detail.phones == ["(480) 555-0134"]
    assert detail.emails == ["me@example.com"]
    assert detail.seller_type == "dealer"


@pytest.mark.parametrize(
    ("status_code", "body", "expected"),
    [
        (200, "<html>a normal posting</html>", craigslist.ListingStatus.ACTIVE),
        (404, "Page Not Found", craigslist.ListingStatus.REMOVED),
        (200, "This posting has been deleted by its author.", craigslist.ListingStatus.REMOVED),
        (200, "This posting has been flagged for removal.", craigslist.ListingStatus.REMOVED),
        (200, "This posting has expired.", craigslist.ListingStatus.EXPIRED),
        (503, "", craigslist.ListingStatus.UNKNOWN),
    ],
)
def test_status_detection(status_code, body, expected):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=body)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert craigslist.check_status(DETAIL_URL, client=client) is expected


def test_removed_listings_do_not_pretend_to_have_details():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Page Not Found")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    detail = craigslist.fetch_detail(DETAIL_URL, client=client)

    assert detail.status is craigslist.ListingStatus.REMOVED
    assert detail.description == ""
    assert detail.images == []


def test_unreachable_listing_is_unknown_not_removed():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network down")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert craigslist.check_status(DETAIL_URL, client=client) is craigslist.ListingStatus.UNKNOWN
