"""Allowlist and scam-signal filters never touch the network."""

from app.models import Deal, LookupLink, SourceInfo
from app.topics import source_infos
from app.trust import (
    filter_live_deals,
    filter_lookup_links,
    filter_source_infos,
    is_allowlisted_url,
    is_verified_lookup_url,
    looks_like_scam,
    sanitize_request_deals,
)


def _deal(title: str, url: str | None, lookup_urls: list[LookupLink] | None = None) -> Deal:
    return Deal(
        id="x",
        title=title,
        acquisition_cost=100,
        market_value=200,
        url=url,
        lookup_urls=lookup_urls or [],
    )


def test_craigslist_and_ebay_https_hosts_are_allowlisted():
    assert is_allowlisted_url("https://phoenix.craigslist.org/view/d/slug/abc")
    assert is_allowlisted_url("https://www.craigslist.org/view/d/slug/abc")
    assert is_allowlisted_url("https://www.ebay.com/itm/123")
    assert is_allowlisted_url("https://ebay.com/itm/123")


def test_http_and_typosquat_hosts_are_rejected():
    assert not is_allowlisted_url("http://phoenix.craigslist.org/view/d/slug/abc")
    assert not is_allowlisted_url("https://craigslist.com/view/d/slug/abc")
    assert not is_allowlisted_url("https://ebay-deals.tk/itm/1")
    assert not is_allowlisted_url("https://secure-ebay.com/itm/1")
    assert not is_allowlisted_url("https://notcraigslist.org/view/d/slug/abc")


def test_unknown_and_shortener_hosts_are_rejected():
    assert not is_allowlisted_url("https://bit.ly/totally-legit")
    assert not is_allowlisted_url("https://tinyurl.com/abc")
    assert not is_allowlisted_url("https://cash.app/pay")
    assert not is_allowlisted_url("https://random-deals.example/item/1")
    assert not is_allowlisted_url(None)


def test_official_lookup_hosts_are_verified_https_only():
    assert is_verified_lookup_url("https://www.zillow.com/homes/Phoenix-AZ_rb/")
    assert is_verified_lookup_url("https://www.kitco.com/")
    assert is_verified_lookup_url("https://www.gia.edu/report-check-landing")
    assert is_verified_lookup_url("https://bstock.com/")
    assert not is_verified_lookup_url("http://www.zillow.com/")
    assert not is_verified_lookup_url("https://zillow-deals.tk/homes")
    assert not is_verified_lookup_url("https://bit.ly/zillow")


def test_gift_card_and_wire_titles_look_like_scams():
    assert looks_like_scam("TV for sale — pay with gift card")
    assert looks_like_scam("House rent, wire transfer only")
    assert looks_like_scam("Pay holding fee on Cash App")
    assert looks_like_scam("Booking fee friends and family")
    assert not looks_like_scam("DeWalt cordless drill")
    assert looks_like_scam("Louis Vuitton replica bag 1:1")
    assert looks_like_scam("Charizard proxy card fake PSA")


def test_filter_keeps_allowlisted_listings_and_marks_them_verified():
    kept = filter_live_deals(
        [_deal("DeWalt cordless drill", "https://www.craigslist.org/view/d/slug/abc")]
    )
    assert len(kept) == 1
    assert kept[0].verified is True


def test_filter_drops_scam_titles_even_on_craigslist():
    kept = filter_live_deals(
        [_deal("Send bitcoin for this sofa", "https://www.craigslist.org/view/d/slug/abc")]
    )
    assert kept == []


def test_filter_strips_unknown_lookup_hosts():
    kept = filter_live_deals(
        [
            _deal(
                "DeWalt cordless drill",
                "https://www.ebay.com/itm/1",
                [
                    LookupLink(name="eBay", url="https://www.ebay.com/sch/i.html?_nkw=drill"),
                    LookupLink(name="Scam", url="https://cheap-gold-deals.tk/x"),
                ],
            )
        ]
    )
    assert [link.url for link in kept[0].lookup_urls] == [
        "https://www.ebay.com/sch/i.html?_nkw=drill"
    ]


def test_filter_lookup_links_keeps_only_official_hosts():
    kept = filter_lookup_links(
        [
            LookupLink(name="Zillow", url="https://www.zillow.com/"),
            LookupLink(name="Fake", url="https://zillow.example/"),
        ]
    )
    assert [link.name for link in kept] == ["Zillow"]


def test_sanitize_request_deals_strips_unknown_urls_and_drops_scam_titles():
    kept = sanitize_request_deals(
        [
            _deal("DeWalt cordless drill", "https://bit.ly/totally-legit"),
            _deal("Pay holding fee first", "https://www.craigslist.org/view/d/slug/abc"),
            _deal("Ryobi saw", "https://www.ebay.com/itm/9"),
        ]
    )
    assert [deal.title for deal in kept] == ["DeWalt cordless drill", "Ryobi saw"]
    assert kept[0].url is None
    assert kept[1].url == "https://www.ebay.com/itm/9"
    assert kept[1].verified is True


def test_source_infos_are_all_verified_official_hosts():
    sources = source_infos()
    assert sources
    assert all(source.verified for source in sources)
    live_urls = [source.url for source in sources if source.kind == "live"]
    assert all(is_allowlisted_url(url) for url in live_urls)
    lookup_urls = [source.url for source in sources if source.kind == "lookup-only"]
    assert all(is_verified_lookup_url(url) for url in lookup_urls)
    names = {source.name for source in sources}
    assert {"Craigslist Phoenix", "eBay", "Zillow", "Kitco", "GIA", "B-Stock"} <= names
    assert "Facebook" not in names
    assert "OfferUp" not in names


def test_filter_source_infos_drops_unknown_hosts():
    kept = filter_source_infos(
        [
            SourceInfo(
                id="scam",
                name="Cheap Gold",
                kind="live",
                topics=["gold"],
                blurb="nope",
                url="https://cheap-gold-deals.tk/",
            ),
            SourceInfo(
                id="craigslist",
                name="Craigslist Phoenix",
                kind="live",
                topics=["tools"],
                blurb="ok",
                url="https://phoenix.craigslist.org/",
                verified=False,
            ),
        ]
    )
    assert [source.id for source in kept] == ["craigslist"]
    assert kept[0].verified is True
