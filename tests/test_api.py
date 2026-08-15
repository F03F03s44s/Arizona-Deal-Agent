"""API tests using FastAPI's TestClient."""

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.transmit import set_http_client

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.json()["version"]


def test_list_deals():
    res = client.get("/api/deals")
    assert res.status_code == 200
    body = res.json()
    assert body["budget"] > 0
    assert len(body["deals"]) >= 1


def test_rank_uses_sample_deals_when_none_given():
    res = client.post("/api/rank", json={"budget": 15000, "deals": []})
    assert res.status_code == 200
    body = res.json()
    assert len(body["ranked"]) >= 1
    assert body["recommendation"] is not None
    assert body["recommendation"]["within_budget"] is True


def test_index_served():
    res = client.get("/")
    assert res.status_code == 200
    assert "Arizona Deal Agent" in res.text
    assert "Send recommendation" in res.text


def test_send_to_inbox_and_list_logs():
    res = client.post(
        "/api/send",
        json={"budget": 15000, "destination": "inbox", "note": "from api"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "sent"
    assert body["destination"] == "inbox"
    assert body["recommendation_title"]
    assert body["payload"]["schema"] == "arizona-deal-agent.transmission.v1"

    outbox = client.get("/api/transmissions").json()
    inbox = client.get("/api/inbox").json()
    assert outbox[0]["id"] == body["id"]
    assert inbox[0]["id"] == body["id"]
    assert inbox[0]["note"] == "from api"


def test_send_webhook_missing_url_is_422():
    res = client.post("/api/send", json={"budget": 15000, "destination": "webhook"})
    assert res.status_code == 422


def test_send_rejects_private_webhook():
    res = client.post(
        "/api/send",
        json={
            "budget": 15000,
            "destination": "webhook",
            "webhook_url": "http://127.0.0.1:9/inbox",
        },
    )
    assert res.status_code == 400
    assert "private" in res.json()["detail"] or "not allowed" in res.json()["detail"]


def test_send_webhook_success_via_mock():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "hooks.example.com"
        return httpx.Response(202, json={"queued": True})

    set_http_client(httpx.Client(transport=httpx.MockTransport(handler)))
    res = client.post(
        "/api/send",
        json={
            "budget": 15000,
            "destination": "webhook",
            "webhook_url": "https://hooks.example.com/deals",
            "include_ranking": False,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "sent"
    assert body["status_code"] == 202
    assert "ranked" not in body["payload"]


def test_external_inbox_post():
    res = client.post(
        "/api/inbox",
        json={
            "schema": "arizona-deal-agent.transmission.v1",
            "note": "partner feed",
            "deal_count": 1,
            "recommendation": {"deal": {"id": "az-999", "title": "Inbound lot"}},
        },
    )
    assert res.status_code == 200
    assert res.json()["recommendation_title"] == "Inbound lot"
    assert client.get("/api/inbox").json()[0]["note"] == "partner feed"
