"""Tests for saved searches and the alert emails they send."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from app.alerts import (
    AlertService,
    ConsoleEmailSender,
    OutgoingEmail,
    SavedSearchStore,
    SmtpEmailSender,
    build_sender_from_env,
)
from app.deals import DealService
from app.models import SavedSearchCreate
from tests.conftest import make_listing
from tests.smtp_stub import StubSmtpServer

# One clear bargain (40 against a 230 median) plus four ordinary drills.
LISTINGS = [
    make_listing("1", "DeWalt cordless drill", 200),
    make_listing("2", "DeWalt cordless drill", 220),
    make_listing("3", "DeWalt cordless drill", 240),
    make_listing("4", "DeWalt cordless drill", 260),
    make_listing("bargain", "DeWalt cordless drill", 40),
]


@dataclass
class RecordingSender:
    """Captures alerts instead of sending them, and can fail on demand."""

    name: str = "recording"
    sent: list[OutgoingEmail] = field(default_factory=list)
    fail_with: str | None = None

    def send(self, message: OutgoingEmail) -> None:
        if self.fail_with:
            raise RuntimeError(self.fail_with)
        self.sent.append(message)


@pytest.fixture
def service(tmp_path):
    def searcher(query, **kwargs):
        return LISTINGS

    store = SavedSearchStore(tmp_path / "saved.json")
    sender = RecordingSender()
    return AlertService(
        store=store,
        sender=sender,
        deals=DealService(searcher=searcher),
    )


def _save(service: AlertService, **overrides):
    payload = {
        "query": "cordless drill",
        "email": "kiet@example.com",
        "budget": 15000.0,
        "min_score": 0.9,
    }
    payload.update(overrides)
    return service.store.add(SavedSearchCreate(**payload))


def test_alert_is_emailed_for_a_high_scoring_deal(service):
    result = service.run(_save(service))

    assert len(result.new_matches) == 1
    assert result.new_matches[0].deal.id == "cl-bargain"
    assert result.alert is not None
    assert result.alert.delivered is True

    (message,) = service.sender.sent
    assert message.to == "kiet@example.com"
    assert "DeWalt cordless drill" in message.subject
    assert "$40" in message.body
    assert "median of 4 similar listings" in message.body
    assert "https://www.craigslist.org/view/d/slug/bargain" in message.body


def test_a_listing_is_only_emailed_once(service):
    search = _save(service)

    first = service.run(search)
    second = service.run(service.store.get(search.id))

    assert len(first.new_matches) == 1
    assert second.new_matches == []
    assert second.alert is None
    # The deal still matches, it has just already been reported.
    assert len(second.matches) == 1
    assert len(service.sender.sent) == 1


def test_a_new_bargain_triggers_a_second_email(service, tmp_path):
    search = _save(service)
    service.run(search)

    service.deals = DealService(
        searcher=lambda query, **kwargs: LISTINGS
        + [make_listing("fresh", "DeWalt cordless drill", 45)]
    )
    result = service.run(service.store.get(search.id))

    assert [m.deal.id for m in result.new_matches] == ["cl-fresh"]
    assert len(service.sender.sent) == 2


def test_failed_delivery_is_retried_next_run(service):
    service.sender.fail_with = "connection refused"
    search = _save(service)

    first = service.run(search)
    assert first.alert is not None
    assert first.alert.delivered is False
    assert first.alert.error == "connection refused"
    assert service.store.get(search.id).notified_deal_ids == []

    service.sender.fail_with = None
    second = service.run(service.store.get(search.id))

    assert len(second.new_matches) == 1
    assert len(service.sender.sent) == 1


def test_threshold_controls_what_alerts(service):
    result = service.run(_save(service, min_score=0.99))
    assert len(result.new_matches) == 1

    relaxed = service.run(_save(service, min_score=0.5, email="other@example.com"))
    assert len(relaxed.new_matches) == 5


def test_over_budget_deals_never_alert(service):
    result = service.run(_save(service, budget=30, min_score=0.0))

    assert result.new_matches == []
    assert service.sender.sent == []


def test_alerts_are_recorded_in_history(service):
    service.run(_save(service))

    (alert,) = service.store.alerts()
    assert alert.transport == "recording"
    assert alert.deal_ids == ["cl-bargain"]
    assert alert.delivered is True


def test_run_all_covers_every_saved_search(service):
    _save(service)
    _save(service, email="second@example.com")

    results = service.run_all()

    assert len(results) == 2
    assert len(service.sender.sent) == 2


def test_saved_searches_survive_a_restart(service, tmp_path):
    search = _save(service)
    service.run(search)

    reopened = SavedSearchStore(service.store.path)
    (restored,) = reopened.list()

    assert restored.id == search.id
    assert restored.email == "kiet@example.com"
    assert restored.notified_deal_ids == ["cl-bargain"]
    assert restored.last_run_at is not None
    assert len(reopened.alerts()) == 1


def test_deleting_a_saved_search_removes_it(service):
    search = _save(service)

    assert service.store.delete(search.id) is True
    assert service.store.delete(search.id) is False
    assert service.store.list() == []


def test_smtp_transport_delivers_a_real_message(service):
    with StubSmtpServer() as smtp:
        service.sender = SmtpEmailSender(
            host="127.0.0.1",
            port=smtp.port,
            sender="agent@localhost",
            use_starttls=False,
        )
        result = service.run(_save(service))

        assert result.alert is not None
        assert result.alert.delivered is True
        assert result.alert.transport == "smtp"

        (raw,) = smtp.messages

    assert "To: kiet@example.com" in raw
    assert "From: agent@localhost" in raw
    assert "Subject: Deal alert: DeWalt cordless drill" in raw
    assert "https://www.craigslist.org/view/d/slug/bargain" in raw


def test_transport_is_chosen_from_the_environment(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    assert isinstance(build_sender_from_env(), ConsoleEmailSender)

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMTP_STARTTLS", "false")
    sender = build_sender_from_env()

    assert isinstance(sender, SmtpEmailSender)
    assert (sender.host, sender.port, sender.use_starttls) == ("smtp.example.com", 2525, False)
