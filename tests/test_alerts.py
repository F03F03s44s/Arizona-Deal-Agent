"""Tests for saved-search alerts."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import alerts, emailer
from app.main import app
from app.models import Deal

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    store = tmp_path / "saved_searches.json"
    log = tmp_path / "alerts.log"
    monkeypatch.setattr(alerts, "STORE_PATH", store)
    monkeypatch.setattr(emailer, "ALERT_LOG", log)
    yield store, log


def _hot_deals(*, query=None, refresh=False, allow_sample_fallback=True):
    return [
        Deal(
            id="hot-1",
            title="Estate sale tool haul (Tempe)",
            category="tools",
            acquisition_cost=200,
            market_value=900,
            source="craigslist",
            url="https://example.com/hot-1",
        )
    ], "craigslist"


def test_create_and_list_saved_search():
    res = client.post(
        "/api/saved-searches",
        json={
            "email": "buyer@example.com",
            "budget": 5000,
            "profit_weight": 0.7,
            "min_score": 0.9,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == "buyer@example.com"
    assert body["min_score"] == 0.9

    listed = client.get("/api/saved-searches")
    assert listed.status_code == 200
    assert len(listed.json()["searches"]) == 1


def test_check_sends_alert_when_score_above_threshold(monkeypatch, isolated_store):
    _store, log = isolated_store
    monkeypatch.setattr(alerts, "load_deals", _hot_deals)

    created = client.post(
        "/api/saved-searches",
        json={
            "email": "alerts@example.com",
            "budget": 5000,
            "profit_weight": 0.8,
            "min_score": 0.9,
        },
    )
    assert created.status_code == 200

    checked = client.post("/api/saved-searches/check?refresh=false")
    assert checked.status_code == 200
    body = checked.json()
    assert body["checked"] == 1
    assert body["alerts_sent"] == 1
    assert log.exists()
    text = log.read_text(encoding="utf-8")
    assert "alerts@example.com" in text
    assert "Estate sale tool haul" in text
