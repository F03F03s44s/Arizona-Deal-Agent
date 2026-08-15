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
    assert body["fetched_at"] is not None
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


def test_rank_scrapes_once_across_many_slider_moves(offline_deal_service):
    for weight in (0.0, 0.25, 0.5, 0.75, 1.0):
        res = client.post(
            "/api/rank",
            json={"budget": 15000, "profit_weight": weight, "query": "cordless drill"},
        )
        assert res.status_code == 200

    # Live re-ranking must not put a scrape in the request path.
    assert len(offline_deal_service) == 1


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


def test_saved_search_lifecycle():
    created = client.post(
        "/api/saved-searches",
        json={"query": "cordless drill", "email": "kiet@example.com", "min_score": 0.9},
    )
    assert created.status_code == 201
    result = created.json()

    # Saving runs the search immediately, so an existing bargain alerts at once.
    assert len(result["new_matches"]) == 1
    assert result["alert"]["delivered"] is True
    assert result["alert"]["email"] == "kiet@example.com"

    listed = client.get("/api/saved-searches").json()
    assert len(listed) == 1
    search_id = listed[0]["id"]
    assert listed[0]["notified_deal_ids"] == ["cl-bargain"]

    rerun = client.post(f"/api/saved-searches/{search_id}/run").json()
    assert rerun["new_matches"] == []
    assert rerun["alert"] is None

    alerts = client.get("/api/alerts").json()
    assert len(alerts) == 1
    assert "DeWalt cordless drill" in alerts[0]["subject"]

    assert client.delete(f"/api/saved-searches/{search_id}").status_code == 204
    assert client.get("/api/saved-searches").json() == []


def test_saved_search_rejects_a_bad_email():
    res = client.post(
        "/api/saved-searches", json={"query": "drill", "email": "not-an-email"}
    )
    assert res.status_code == 422


def test_missing_saved_search_is_reported():
    assert client.post("/api/saved-searches/nope/run").status_code == 404
    assert client.delete("/api/saved-searches/nope").status_code == 404


def test_index_served():
    res = client.get("/")
    assert res.status_code == 200
    assert "Arizona Deal Agent" in res.text
    assert "topics" in res.text
    assert "LIVE_POLL_MS" in res.text
    assert "refresh=true" in res.text
