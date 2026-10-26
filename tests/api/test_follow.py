"""Follow path: SLI 2 (valid redirect or correct 404), SLI 3, SLI 5."""

URL = "https://example.com/some/long/path?a=1&b=2"


def test_follow_unknown_code_is_404(client):
    assert client.get("/nope12").status_code == 404


def test_stats_unknown_code_is_404(client):
    assert client.get("/api/links/nope12/stats").status_code == 404


def test_follow_unknown_code_does_not_create_stats(client):
    client.get("/nope12")
    assert client.get("/api/links").json() == []


def test_follow_redirects_to_stored_url(client):
    code = client.post("/api/links", json={"url": URL}).json()["code"]
    r = client.get(f"/{code}")
    assert r.status_code == 307
    assert r.headers["location"] == URL


def test_clicks_equal_follows(client):
    code = client.post("/api/links", json={"url": URL}).json()["code"]
    for _ in range(3):
        client.get(f"/{code}")
    assert client.get(f"/api/links/{code}/stats").json()["clicks"] == 3
