"""Saved searches and the email alerts they produce.

A saved search is a standing query the agent re-runs on a schedule. Whenever a
listing scores at or above the search's threshold, its owner gets one email —
and only one, because alerted listing ids are remembered on the search.
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.message import EmailMessage as MimeMessage
from pathlib import Path
from typing import Protocol

from .agent import rank_deals
from .deals import DealService, deal_service
from .models import (
    Alert,
    SavedSearch,
    SavedSearchCreate,
    SavedSearchRunResult,
    ScoredDeal,
)

logger = logging.getLogger(__name__)

# Cap on remembered alert history so the store cannot grow without bound.
MAX_ALERTS = 200
MAX_NOTIFIED_IDS = 500


@dataclass(frozen=True)
class OutgoingEmail:
    """An alert email ready to hand to a transport."""

    to: str
    subject: str
    body: str


class EmailSender(Protocol):
    """Delivers alert emails. Raises on failure."""

    name: str

    def send(self, message: OutgoingEmail) -> None: ...


@dataclass
class ConsoleEmailSender:
    """Writes alerts to the log instead of sending them.

    Used when no SMTP server is configured, so the feature stays observable in
    development rather than failing or silently dropping alerts.
    """

    name: str = "console"

    def send(self, message: OutgoingEmail) -> None:
        logger.info(
            "ALERT EMAIL (not sent, no SMTP configured)\nTo: %s\nSubject: %s\n\n%s",
            message.to,
            message.subject,
            message.body,
        )


@dataclass
class SmtpEmailSender:
    """Sends alerts through an SMTP server."""

    host: str
    port: int = 587
    username: str | None = None
    password: str | None = None
    sender: str = "arizona-deal-agent@localhost"
    use_starttls: bool = True
    timeout: float = 20.0
    name: str = "smtp"

    def send(self, message: OutgoingEmail) -> None:
        mime = MimeMessage()
        mime["From"] = self.sender
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.body)

        with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
            if self.use_starttls:
                smtp.starttls()
            if self.username:
                smtp.login(self.username, self.password or "")
            smtp.send_message(mime)


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def build_sender_from_env() -> EmailSender:
    """Pick an email transport from ``SMTP_*`` environment variables."""
    host = os.getenv("SMTP_HOST")
    if not host:
        return ConsoleEmailSender()

    return SmtpEmailSender(
        host=host,
        port=int(os.getenv("SMTP_PORT", "587")),
        username=os.getenv("SMTP_USERNAME") or None,
        password=os.getenv("SMTP_PASSWORD") or None,
        sender=os.getenv("SMTP_FROM", "arizona-deal-agent@localhost"),
        use_starttls=_env_flag("SMTP_STARTTLS", True),
    )


def _money(value: float) -> str:
    return f"${value:,.0f}"


def build_alert_email(search: SavedSearch, matches: list[ScoredDeal]) -> OutgoingEmail:
    """Compose the alert email for newly-matched deals."""
    count = len(matches)
    headline = matches[0].deal.title
    subject = (
        f"Deal alert: {headline}"
        if count == 1
        else f"Deal alert: {count} new deals for '{search.query}'"
    )

    lines = [
        f"Your saved search '{search.query}' found {count} "
        f"deal{'s' if count != 1 else ''} scoring {search.min_score:.2f} or better.",
        "",
    ]
    for scored in matches:
        deal = scored.deal
        lines.extend(
            [
                f"{deal.title}",
                f"  Score:      {scored.score:.3f}",
                f"  Asking:     {_money(deal.acquisition_cost)}",
                f"  Comparable: {_money(deal.market_value)} "
                f"(median of {deal.comparable_count} similar listings)",
                f"  Est. profit:{_money(scored.profit)} ({scored.profit_margin * 100:.0f}% margin)",
            ]
        )
        if deal.location:
            lines.append(f"  Location:   {deal.location}")
        if deal.url:
            lines.append(f"  Listing:    {deal.url}")
        lines.append("")

    lines.append(
        f"Budget {_money(search.budget)} - profit weight {search.profit_weight:.2f}"
    )
    lines.append("Sent by Arizona Deal Agent.")

    return OutgoingEmail(to=search.email, subject=subject, body="\n".join(lines))


class SavedSearchStore:
    """JSON-file store for saved searches and sent alerts."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._searches: dict[str, SavedSearch] = {}
        self._alerts: list[Alert] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read saved searches from %s: %s", self.path, exc)
            return

        for item in raw.get("saved_searches", []):
            try:
                search = SavedSearch.model_validate(item)
            except ValueError as exc:
                logger.warning("Skipping malformed saved search: %s", exc)
                continue
            self._searches[search.id] = search

        for item in raw.get("alerts", []):
            try:
                self._alerts.append(Alert.model_validate(item))
            except ValueError as exc:
                logger.warning("Skipping malformed alert: %s", exc)

    def _flush(self) -> None:
        payload = {
            "saved_searches": [s.model_dump(mode="json") for s in self._searches.values()],
            "alerts": [a.model_dump(mode="json") for a in self._alerts[-MAX_ALERTS:]],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2))
        temp.replace(self.path)

    def list(self) -> list[SavedSearch]:
        with self._lock:
            return sorted(self._searches.values(), key=lambda s: s.created_at)

    def get(self, search_id: str) -> SavedSearch | None:
        with self._lock:
            return self._searches.get(search_id)

    def add(self, create: SavedSearchCreate) -> SavedSearch:
        search = SavedSearch(
            id=uuid.uuid4().hex[:12],
            created_at=datetime.now(UTC),
            **create.model_dump(),
        )
        with self._lock:
            self._searches[search.id] = search
            self._flush()
        return search

    def save(self, search: SavedSearch) -> None:
        with self._lock:
            self._searches[search.id] = search
            self._flush()

    def delete(self, search_id: str) -> bool:
        with self._lock:
            removed = self._searches.pop(search_id, None) is not None
            if removed:
                self._flush()
            return removed

    def clear(self) -> None:
        with self._lock:
            self._searches.clear()
            self._alerts.clear()
            self._flush()

    def add_alert(self, alert: Alert) -> None:
        with self._lock:
            self._alerts.append(alert)
            del self._alerts[:-MAX_ALERTS]
            self._flush()

    def alerts(self, limit: int = 20) -> list[Alert]:
        with self._lock:
            return list(reversed(self._alerts[-limit:]))


@dataclass
class AlertService:
    """Runs saved searches and emails their new high-scoring matches."""

    store: SavedSearchStore
    sender: EmailSender = field(default_factory=build_sender_from_env)
    deals: DealService = field(default_factory=lambda: deal_service)

    def run(self, search: SavedSearch) -> SavedSearchRunResult:
        sourced = self.deals.get_deals(search.query)
        ranked = rank_deals(sourced.deals, search.budget, search.profit_weight)

        matches = [
            scored
            for scored in ranked.ranked
            if scored.within_budget and scored.score >= search.min_score
        ]
        already_seen = set(search.notified_deal_ids)
        new_matches = [m for m in matches if m.deal.id not in already_seen]

        alert: Alert | None = None
        if new_matches:
            alert = self._deliver(search, new_matches)

        search.last_run_at = datetime.now(UTC)
        if alert is not None and alert.delivered:
            # Only remember ids that actually went out, so a failed send is
            # retried on the next run instead of being silently swallowed.
            search.notified_deal_ids = (
                search.notified_deal_ids + [m.deal.id for m in new_matches]
            )[-MAX_NOTIFIED_IDS:]
        self.store.save(search)

        return SavedSearchRunResult(
            saved_search_id=search.id,
            query=search.query,
            deals_considered=len(sourced.deals),
            matches=matches,
            new_matches=new_matches,
            alert=alert,
            warning=sourced.warning,
        )

    def _deliver(self, search: SavedSearch, matches: list[ScoredDeal]) -> Alert:
        message = build_alert_email(search, matches)
        delivered, error = True, None
        try:
            self.sender.send(message)
        except Exception as exc:  # noqa: BLE001 - any transport failure is reportable
            delivered, error = False, str(exc)
            logger.warning("Alert email to %s failed: %s", message.to, exc)

        alert = Alert(
            id=uuid.uuid4().hex[:12],
            saved_search_id=search.id,
            query=search.query,
            email=message.to,
            subject=message.subject,
            body=message.body,
            sent_at=datetime.now(UTC),
            delivered=delivered,
            transport=self.sender.name,
            error=error,
            deal_ids=[m.deal.id for m in matches],
        )
        self.store.add_alert(alert)
        return alert

    def run_all(self) -> list[SavedSearchRunResult]:
        return [self.run(search) for search in self.store.list()]
