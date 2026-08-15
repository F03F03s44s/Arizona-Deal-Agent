"""API tests using FastAPI's TestClient."""

from fastapi.testclient import TestClient

from app.main import app
from app.models import Deal

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_list_deals(monkeypatch):
    monkeypatch.setattr(
        "app.main.load_deals",
        lambda query=None, refresh=False: (
            [
                Deal(
                    id="t1",
                    title="Test desk (Phoenix)",
                    category="furniture",
                    acquisition_cost=100,
                    market_value=180,
                    source="craigslist",
                )
            ],
            "craigslist",
        ),
    )
    res = client.get("/api/deals")
    assert res.status_code == 200
    body = res.json()
    assert body["budget"] > 0
    assert body["source"] == "craigslist"
    assert len(body["deals"]) >= 1


def test_rank_uses_live_loader_when_none_given(monkeypatch):
    monkeypatch.setattr(
        "app.main.load_deals",
        lambda query=None, refresh=False: (
            [
                Deal(
                    id="t1",
                    title="Test desk (Phoenix)",
                    category="furniture",
                    acquisition_cost=100,
                    market_value=180,
                    source="craigslist",
                )
            ],
            "craigslist",
        ),
    )
    res = client.post("/api/rank", json={"budget": 15000, "deals": []})
    assert res.status_code == 200
    body = res.json()
    assert len(body["ranked"]) >= 1
    assert body["source"] == "craigslist"
    assert body["recommendation"] is not None
    assert body["recommendation"]["within_budget"] is True


def test_index_served():
    res = client.get("/")
    assert res.status_code == 200
    assert "Arizona Deal Agent" in res.text


def test_index_live_slider_and_alerts():
    res = client.get("/")
    assert res.status_code == 200
    body = res.text
    assert "How to use" in body
    assert "Live ranking" in body
    assert "Saved search email alerts" in body
    assert "scheduleRank" in body
    assert "Rank deals" not in body
    assert "Max affordability" in body
    assert "Tight $2,000" in body
