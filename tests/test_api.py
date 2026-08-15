"""API tests using FastAPI's TestClient."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_list_deals():
    res = client.get("/api/deals")
    assert res.status_code == 200
    body = res.json()
    assert body["budget"] > 0
    assert len(body["deals"]) > 5


def test_rank_uses_sample_deals_when_none_given():
    res = client.post("/api/rank", json={"budget": 15000, "deals": []})
    assert res.status_code == 200
    body = res.json()
    assert len(body["ranked"]) > 5
    assert len(body["ranked"]) <= 100
    assert body["recommendation"] is not None
    assert body["recommendation"]["within_budget"] is True


def test_index_served():
    res = client.get("/")
    assert res.status_code == 200
    assert "Arizona Deal Agent" in res.text


def test_index_includes_how_to_use():
    res = client.get("/")
    assert res.status_code == 200
    body = res.text
    assert "How to use" in body
    assert "Rank deals" in body
    assert "Max affordability" in body
    assert "Tight $2,000" in body
    assert "Houses" in body


def test_rank_houses_category():
    res = client.post(
        "/api/rank",
        json={"budget": 350000, "profit_weight": 0.6, "deals": [], "category": "house"},
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["ranked"]) > 5
    assert all(
        row["deal"]["category"] in {"house", "real-estate"} for row in body["ranked"]
    )
    assert body["recommendation"] is not None
    assert "house" in body["recommendation"]["deal"]["title"].lower() or body[
        "recommendation"
    ]["deal"]["category"] in {"house", "real-estate"}
