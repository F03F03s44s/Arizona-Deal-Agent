"""Allowlist and scam-signal filters never touch the network."""

from app.models import Deal
from app.trust import filter_live_deals, is_allowlisted_url, looks_like_scam


def _deal(title: str, url: str | None) -> Deal:
    return Deal(
        id="x",
        title=title,
        acquisition_cost=100,
        market_value=200,
        url=url,
    )


def test_craigslist_host_is_allowlisted():
    assert is_allowlisted_url("https://phoenix.craigslist.org/view/d/slug/abc")
    assert is_allowlisted_url("https://www.craigslist.org/view/d/slug/abc")


def test_unknown_and_shortener_hosts_are_rejected():
    assert not is_allowlisted_url("https://bit.ly/totally-legit")
    assert not is_allowlisted_url("https://random-deals.example/item/1")
    assert not is_allowlisted_url(None)


def test_gift_card_and_wire_titles_look_like_scams():
    assert looks_like_scam("TV for sale — pay with gift card")
    assert looks_like_scam("House rent, wire transfer only")
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
