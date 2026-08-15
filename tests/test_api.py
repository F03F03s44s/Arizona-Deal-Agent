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
    assert len(body["deals"]) >= 1


def test_deals_come_from_craigslist():
    res = client.get("/api/deals", params={"query": "cordless drill"})
    body = res.json()

    assert body["source"] == "craigslist"
    assert body["query"] == "cordless drill"
    assert body["warning"] is None
    deal = body["deals"][0]
    assert deal["url"].startswith("https://www.craigslist.org/view/d/")
    assert deal["comparable_count"] >= 1


def test_rank_uses_sample_deals_when_none_given():
    res = client.post("/api/rank", json={"budget": 15000, "deals": []})
    assert res.status_code == 200
    body = res.json()
    assert len(body["ranked"]) >= 1
    assert body["recommendation"] is not None
    assert body["recommendation"]["within_budget"] is True


def test_rank_honours_the_profit_weight():
    def top(weight: float) -> str:
        res = client.post(
            "/api/rank",
            json={"budget": 300, "profit_weight": weight, "query": "cordless drill"},
        )
        return res.json()["ranked"][0]["deal"]["id"]

    # The 40-dollar drill wins on both axes; the 260-dollar one is over budget
    # at this ceiling, so weighting must not promote it.
    assert top(1.0) == "cl-bargain"
    assert top(0.0) == "cl-bargain"


def test_rank_accepts_caller_supplied_deals():
    res = client.post(
        "/api/rank",
        json={
            "budget": 1000,
            "deals": [
                {"id": "x", "title": "x", "acquisition_cost": 100, "market_value": 400}
            ],
        },
    )
    body = res.json()

    assert body["source"] == "request"
    assert len(body["ranked"]) == 1


def test_refresh_forces_a_rescrape(offline_deal_service):
    client.get("/api/deals", params={"query": "cordless drill"})
    client.get("/api/deals", params={"query": "cordless drill"})
    assert len(offline_deal_service) == 1

    client.get("/api/deals", params={"query": "cordless drill", "refresh": True})
    assert len(offline_deal_service) == 2


def test_index_served():
    res = client.get("/")
    assert res.status_code == 200
    assert "Arizona Deal Agent" in res.text
