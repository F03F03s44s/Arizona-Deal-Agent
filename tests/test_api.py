import pytest
from fastapi.testclient import TestClient

from deal_agent.api import app, get_ranked_deals


@pytest.fixture(scope="module")
def client():
    get_ranked_deals.cache_clear()
    with TestClient(app) as c:
        yield c


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_deals_ranked_best_first(client):
    data = client.get("/api/deals").json()
    assert data["total"] >= 50
    scores = [d["deal_score"] for d in data["deals"]]
    assert scores == sorted(scores, reverse=True)
    top = data["deals"][0]
    assert {"listing", "deal_score", "breakdown", "reasons"} <= top.keys()
    assert {"value", "yield", "motivation", "risk"} <= top["breakdown"].keys()


def test_city_filter(client):
    data = client.get("/api/deals", params={"city": "phoenix"}).json()
    assert data["total"] > 0
    assert all(d["listing"]["city"] == "Phoenix" for d in data["deals"])


def test_max_price_and_min_beds(client):
    data = client.get("/api/deals", params={"max_price": 400_000, "min_beds": 3}).json()
    assert data["total"] > 0
    for d in data["deals"]:
        assert d["listing"]["price"] <= 400_000
        assert d["listing"]["beds"] >= 3


def test_limit(client):
    data = client.get("/api/deals", params={"limit": 5}).json()
    assert data["returned"] == 5
    assert data["total"] > 5


def test_deal_detail_and_404(client):
    first = client.get("/api/deals", params={"limit": 1}).json()["deals"][0]
    listing_id = first["listing"]["id"]
    assert client.get(f"/api/deals/{listing_id}").json()["listing"]["id"] == listing_id
    assert client.get("/api/deals/NOPE-999").status_code == 404


def test_cities_endpoint(client):
    cities = client.get("/api/cities").json()
    assert len(cities) >= 10
    phoenix = next(c for c in cities if c["city"] == "Phoenix")
    assert phoenix["count"] > 0
    assert phoenix["median_price"] > 0


def test_index_serves_ui(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Arizona Deal Agent" in res.text
