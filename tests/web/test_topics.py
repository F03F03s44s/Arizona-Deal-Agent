"""Topic pages and verified-source APIs."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

EXPECTED_TOPICS = {"property", "household", "electronics", "furniture", "autos", "tools"}


def test_topics_list_covers_household_electronics_houses_cars_furniture():
    body = client.get("/api/topics").json()
    ids = {row["id"] for row in body}
    assert EXPECTED_TOPICS <= ids
    titles = {row["title"] for row in body}
    assert {"Houses", "Household", "Electronics", "Furniture", "Cars", "Tools"} <= titles


def test_topic_pages_are_served():
    for path in ("/houses", "/household", "/electronics", "/furniture", "/cars", "/tools"):
        res = client.get(path)
        assert res.status_code == 200, path
        assert "Arizona Deal Agent" in res.text
        assert "Household" in res.text or "topics" in res.text


def test_unknown_topic_page_is_404():
    assert client.get("/not-a-topic").status_code == 404


def test_unknown_topic_api_is_404():
    assert client.get("/api/deals", params={"topic": "timeshares"}).status_code == 404


def test_property_topic_includes_verified_arizona_houses():
    body = client.get("/api/deals", params={"topic": "houses"}).json()
    assert body["topic"] == "property"
    assert "verified-catalog" in body["source"]
    ids = {deal["id"] for deal in body["deals"]}
    assert "cat-AZ-003" in ids
    house = next(deal for deal in body["deals"] if deal["id"] == "cat-AZ-003")
    assert house["verified"] is True
    assert house["location"] == "Tucson, AZ"
    assert any(link["name"] == "Zillow" for link in house["lookup_urls"])


def test_property_query_filters_the_catalog_by_city():
    body = client.get("/api/deals", params={"topic": "property", "query": "Tucson"}).json()
    cities = {deal["location"] for deal in body["deals"] if deal["id"].startswith("cat-")}
    assert cities == {"Tucson, AZ"}


def test_household_topic_uses_the_household_craigslist_path(offline_deal_service):
    res = client.get("/api/deals", params={"topic": "household"})
    assert res.status_code == 200
    assert offline_deal_service
    _query, kwargs = offline_deal_service[0]
    assert kwargs.get("search_path") == "hsh"


def test_electronics_and_cars_use_their_craigslist_sections(offline_deal_service):
    client.get("/api/deals", params={"topic": "electronics"})
    client.get("/api/deals", params={"topic": "cars"})
    paths = [kwargs.get("search_path") for _query, kwargs in offline_deal_service]
    assert "ele" in paths
    assert "cta" in paths


def test_sources_list_marks_zillow_as_lookup_only():
    body = client.get("/api/sources").json()
    zillow = next(row for row in body if row["name"] == "Zillow")
    assert zillow["kind"] == "lookup-only"
    craigslist = next(row for row in body if row["id"] == "craigslist")
    assert craigslist["kind"] == "live"


def test_rank_on_the_houses_page_recommends_a_catalog_deal():
    res = client.post(
        "/api/rank",
        json={"budget": 350000, "deals": [], "topic": "houses", "query": "arizona house"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["topic"] == "property"
    assert body["recommendation"] is not None
    assert body["recommendation"]["deal"]["id"].startswith("cat-")
