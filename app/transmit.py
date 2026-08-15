"""Outbound data transmission for ranked Arizona deals.

The agent can deliver a ranking payload to:

- ``inbox`` — the in-process inbox (default, no network)
- ``webhook`` — an HTTP POST to a caller-provided https URL
- ``log`` — record the payload locally without delivering it
"""

from __future__ import annotations

import ipaddress
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import urlparse

import httpx

from . import __version__
from .models import RankResponse, TransmissionRecord

SCHEMA = "arizona-deal-agent.transmission.v1"
USER_AGENT = f"ArizonaDealAgent/{__version__}"
WEBHOOK_TIMEOUT = 10.0

BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "metadata.google.internal",
    "metadata.google.com",
}

Destination = Literal["inbox", "webhook", "log"]
PayloadFormat = Literal["json", "slack"]


class TransmissionError(ValueError):
    """Raised when a send request is invalid before delivery is attempted."""


class TransmissionStore:
    """Thread-safe ring buffer of sent and received transmissions."""

    def __init__(self, max_items: int = 100) -> None:
        self.max_items = max_items
        self._lock = threading.Lock()
        self.outbox: list[TransmissionRecord] = []
        self.inbox: list[TransmissionRecord] = []

    def _prepend(self, bucket: list[TransmissionRecord], record: TransmissionRecord) -> None:
        bucket.insert(0, record)
        del bucket[self.max_items :]

    def add_outbox(self, record: TransmissionRecord) -> TransmissionRecord:
        with self._lock:
            self._prepend(self.outbox, record)
        return record

    def add_inbox(self, record: TransmissionRecord) -> TransmissionRecord:
        with self._lock:
            self._prepend(self.inbox, record)
        return record

    def list_outbox(self) -> list[TransmissionRecord]:
        with self._lock:
            return list(self.outbox)

    def list_inbox(self) -> list[TransmissionRecord]:
        with self._lock:
            return list(self.inbox)

    def clear(self) -> None:
        with self._lock:
            self.outbox.clear()
            self.inbox.clear()


STORE = TransmissionStore()
_http_client_override: httpx.Client | None = None


def reset_stores() -> None:
    """Clear in-memory inbox/outbox. Used by tests."""
    STORE.clear()


def set_http_client(client: httpx.Client | None) -> None:
    """Inject an httpx client (for mocked webhook tests)."""
    global _http_client_override
    _http_client_override = client


def validate_webhook_url(url: str) -> str:
    """Accept only public http(s) URLs. Reject private/loopback/metadata hosts."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise TransmissionError("webhook URL must use http or https")
    host = (parsed.hostname or "").lower()
    if not host:
        raise TransmissionError("webhook URL must include a hostname")
    if host in BLOCKED_HOSTS or host.endswith(".local") or host.endswith(".internal"):
        raise TransmissionError("webhook URL host is not allowed")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return url.strip()
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        raise TransmissionError("webhook URL must not target a private address")
    return url.strip()


def webhook_host(url: str | None) -> str | None:
    if not url:
        return None
    return urlparse(url).hostname


def build_payload(
    ranking: RankResponse,
    *,
    note: str | None = None,
    include_ranking: bool = True,
) -> dict[str, Any]:
    """Build the versioned JSON envelope posted to destinations."""
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "source": "arizona-deal-agent",
        "version": __version__,
        "note": note,
        "budget": ranking.budget,
        "profit_weight": ranking.profit_weight,
        "recommendation": (
            ranking.recommendation.model_dump() if ranking.recommendation else None
        ),
    }
    if include_ranking:
        payload["ranked"] = [item.model_dump() for item in ranking.ranked]
        payload["deal_count"] = len(ranking.ranked)
    else:
        payload["deal_count"] = 1 if ranking.recommendation else 0
    return payload


def build_slack_text(payload: dict[str, Any]) -> str:
    rec = payload.get("recommendation")
    budget = payload.get("budget")
    if not rec:
        return f"Arizona Deal Agent: no in-budget recommendation (budget ${budget:,.0f})."
    deal = rec["deal"]
    return (
        f"Arizona Deal Agent recommendation: *{deal['title']}* — "
        f"profit ${rec['profit']:,.0f} ({rec['profit_margin']:.0%}), "
        f"cost ${deal['acquisition_cost']:,.0f}, score {rec['score']:.3f}."
    )


def _delivery_body(payload: dict[str, Any], payload_format: PayloadFormat) -> dict[str, Any]:
    if payload_format == "slack":
        return {"text": build_slack_text(payload)}
    return payload


def _record(
    *,
    destination: Destination,
    status: Literal["sent", "failed", "logged"],
    payload: dict[str, Any],
    webhook_url: str | None = None,
    status_code: int | None = None,
    error: str | None = None,
    note: str | None = None,
) -> TransmissionRecord:
    rec = payload.get("recommendation") or {}
    deal = rec.get("deal") or {}
    return TransmissionRecord(
        id=str(uuid.uuid4()),
        sent_at=datetime.now(timezone.utc),
        destination=destination,
        status=status,
        webhook_host=webhook_host(webhook_url),
        status_code=status_code,
        error=error,
        note=note,
        recommendation_id=deal.get("id"),
        recommendation_title=deal.get("title"),
        deal_count=int(payload.get("deal_count") or 0),
        payload=payload,
    )


def _post_webhook(url: str, body: dict[str, Any]) -> httpx.Response:
    client = _http_client_override
    if client is not None:
        return client.post(
            url,
            json=body,
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
        )
    with httpx.Client(timeout=WEBHOOK_TIMEOUT, follow_redirects=False) as owned:
        return owned.post(
            url,
            json=body,
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
        )


def transmit(
    ranking: RankResponse,
    *,
    destination: Destination = "inbox",
    webhook_url: str | None = None,
    note: str | None = None,
    include_ranking: bool = True,
    payload_format: PayloadFormat = "json",
) -> TransmissionRecord:
    """Rank-adjacent send: deliver ``ranking`` to the chosen destination."""
    if destination == "webhook":
        if not webhook_url:
            raise TransmissionError("webhook_url is required when destination is webhook")
        webhook_url = validate_webhook_url(webhook_url)

    payload = build_payload(ranking, note=note, include_ranking=include_ranking)
    body = _delivery_body(payload, payload_format)

    if destination == "log":
        record = _record(
            destination="log",
            status="logged",
            payload=payload,
            note=note,
        )
        return STORE.add_outbox(record)

    if destination == "inbox":
        record = _record(
            destination="inbox",
            status="sent",
            payload=payload,
            note=note,
        )
        STORE.add_inbox(record)
        return STORE.add_outbox(record)

    try:
        response = _post_webhook(webhook_url or "", body)
        status: Literal["sent", "failed"] = (
            "sent" if 200 <= response.status_code < 300 else "failed"
        )
        error = None if status == "sent" else f"webhook returned HTTP {response.status_code}"
        record = _record(
            destination="webhook",
            status=status,
            payload=payload,
            webhook_url=webhook_url,
            status_code=response.status_code,
            error=error,
            note=note,
        )
    except httpx.HTTPError as exc:
        record = _record(
            destination="webhook",
            status="failed",
            payload=payload,
            webhook_url=webhook_url,
            error=str(exc) or exc.__class__.__name__,
            note=note,
        )
    return STORE.add_outbox(record)


def receive_inbox(payload: dict[str, Any], *, note: str | None = None) -> TransmissionRecord:
    """Accept an inbound transmission (external POST to /api/inbox)."""
    rec = payload.get("recommendation") or {}
    deal = rec.get("deal") or {}
    record = TransmissionRecord(
        id=str(uuid.uuid4()),
        sent_at=datetime.now(timezone.utc),
        destination="inbox",
        status="sent",
        note=note or payload.get("note"),
        recommendation_id=deal.get("id"),
        recommendation_title=deal.get("title"),
        deal_count=int(payload.get("deal_count") or 0),
        payload=payload,
    )
    return STORE.add_inbox(record)
