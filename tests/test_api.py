"""HTTP API and the static UI it serves."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from arizona_deal_agent.web.app import app


@pytest.fixture
def client(monkeypatch, hud_payload):
    """A client whose live source is stubbed, so tests never touch the network."""
    from arizona_deal_agent.sources import hud_reo as hud_module

    monkeypatch.setattr(hud_module, "http_get_json", lambda *a, **k: hud_payload)
    return TestClient(app)


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_sources_endpoint(client):
    names = {source["name"] for source in client.get("/api/sources").json()["sources"]}
    assert names == {"hud-reo", "hud-reo-all", "sample"}


def test_market_endpoint_describes_the_snapshot(client):
    payload = client.get("/api/market").json()
    assert payload["zip_count"] > 100
    assert payload["value_as_of"]
    assert payload["median_value"] > 0


def test_search_returns_ranked_deals(client):
    payload = client.post("/api/search", json={"sources": ["sample"], "top": 5}).json()

    assert len(payload["deals"]) == 5
    assert payload["best"]["id"] == payload["deals"][0]["id"]
    scores = [deal["scores"]["composite"] for deal in payload["deals"]]
    assert scores == sorted(scores, reverse=True)


def test_search_includes_the_live_source(client):
    payload = client.post("/api/search", json={"sources": ["hud-reo"]}).json()

    assert payload["counts"]["found"] == 1
    deal = payload["deals"][0]
    assert deal["source"] == "hud-reo"
    assert deal["inputs"]["price_is_estimated"] is True
    assert deal["warnings"]


def test_search_applies_a_budget(client):
    payload = client.post(
        "/api/search", json={"sources": ["sample"], "max_price": 250_000, "include_over_budget": False}
    ).json()

    assert payload["deals"]
    assert all(deal["inputs"]["price"] <= 250_000 for deal in payload["deals"])
    assert payload["counts"]["over_budget"] > 0


def test_search_applies_a_city_filter(client):
    payload = client.post("/api/search", json={"sources": ["sample"], "cities": ["Tucson"]}).json()
    assert {deal["city"] for deal in payload["deals"]} == {"Tucson"}


def test_search_rejects_a_source_that_is_not_built_in(client):
    """A path here would let a caller read files off the server."""
    response = client.post("/api/search", json={"sources": ["/etc/passwd.csv"]})

    assert response.status_code == 400
    assert "unknown source" in response.json()["detail"]


def test_search_rejects_an_empty_source_list(client):
    assert client.post("/api/search", json={"sources": []}).status_code == 400


def test_search_validates_its_numbers(client):
    assert client.post("/api/search", json={"sources": ["sample"], "max_price": -5}).status_code == 422
    assert client.post("/api/search", json={"sources": ["sample"], "term": 0}).status_code == 422


def test_weights_reach_the_scoring_engine(client):
    body = {"sources": ["sample"], "weight_discount": 1, "weight_profit": 0, "weight_afford": 0}
    deal = client.post("/api/search", json=body).json()["deals"][0]
    assert deal["scores"]["composite"] == deal["scores"]["discount"]


def test_index_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Arizona Deal Agent" in response.text


def test_static_assets_are_served(client):
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/styles.css").status_code == 200
