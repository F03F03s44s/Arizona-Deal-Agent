"""Unit tests for deal data transmission."""

import httpx
import pytest

from app.agent import rank_deals
from app.data import SAMPLE_DEALS
from app.transmit import (
    STORE,
    TransmissionError,
    build_payload,
    build_slack_text,
    set_http_client,
    transmit,
    validate_webhook_url,
)


def _ranking():
    return rank_deals(SAMPLE_DEALS, budget=15000, profit_weight=0.6)


def test_validate_webhook_url_accepts_https():
    assert validate_webhook_url("https://hooks.example.com/deals") == (
        "https://hooks.example.com/deals"
    )


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/x",
        "https://localhost/inbox",
        "http://127.0.0.1/inbox",
        "https://10.0.0.5/hook",
        "https://metadata.google.internal/",
        "https://service.internal/hook",
        "not-a-url",
    ],
)
def test_validate_webhook_url_rejects_unsafe(url):
    with pytest.raises(TransmissionError):
        validate_webhook_url(url)


def test_build_payload_includes_schema_and_recommendation():
    payload = build_payload(_ranking(), note="daily pick")
    assert payload["schema"] == "arizona-deal-agent.transmission.v1"
    assert payload["note"] == "daily pick"
    assert payload["recommendation"]["within_budget"] is True
    assert payload["deal_count"] == len(SAMPLE_DEALS)
    assert len(payload["ranked"]) == len(SAMPLE_DEALS)


def test_build_payload_can_omit_full_ranking():
    payload = build_payload(_ranking(), include_ranking=False)
    assert "ranked" not in payload
    assert payload["deal_count"] == 1
    assert payload["recommendation"] is not None


def test_slack_text_mentions_recommendation_title():
    payload = build_payload(_ranking())
    text = build_slack_text(payload)
    assert "Arizona Deal Agent recommendation" in text
    assert payload["recommendation"]["deal"]["title"] in text


def test_inbox_send_appears_in_outbox_and_inbox():
    record = transmit(_ranking(), destination="inbox", note="pm review")
    assert record.status == "sent"
    assert record.destination == "inbox"
    assert record.note == "pm review"
    assert record.recommendation_title
    assert STORE.list_outbox()[0].id == record.id
    assert STORE.list_inbox()[0].id == record.id


def test_log_only_does_not_fill_inbox():
    record = transmit(_ranking(), destination="log")
    assert record.status == "logged"
    assert STORE.list_outbox()[0].id == record.id
    assert STORE.list_inbox() == []


def test_webhook_send_posts_json_envelope():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"ok": True})

    set_http_client(httpx.Client(transport=httpx.MockTransport(handler)))
    record = transmit(
        _ranking(),
        destination="webhook",
        webhook_url="https://hooks.example.com/deals",
        note="wire it",
    )
    assert record.status == "sent"
    assert record.status_code == 200
    assert record.webhook_host == "hooks.example.com"
    assert len(captured) == 1
    assert captured[0].url.host == "hooks.example.com"
    body = captured[0].read()
    assert b"arizona-deal-agent.transmission.v1" in body
    assert b"wire it" in body


def test_webhook_slack_format_wraps_text():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(204)

    set_http_client(httpx.Client(transport=httpx.MockTransport(handler)))
    record = transmit(
        _ranking(),
        destination="webhook",
        webhook_url="https://hooks.slack.example/services/T/B/X",
        payload_format="slack",
    )
    assert record.status == "sent"
    assert b'"text":' in captured[0].read()


def test_webhook_http_error_is_recorded_as_failed():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="busy")

    set_http_client(httpx.Client(transport=httpx.MockTransport(handler)))
    record = transmit(
        _ranking(),
        destination="webhook",
        webhook_url="https://hooks.example.com/deals",
    )
    assert record.status == "failed"
    assert record.status_code == 503
    assert record.error


def test_webhook_requires_url():
    with pytest.raises(TransmissionError):
        transmit(_ranking(), destination="webhook")
