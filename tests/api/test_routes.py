"""Route contract: each endpoint's status code and response shape, nothing more.

Values (exact URL, click counts) are asserted in test_follow.py and the unit tests;
input validation lives in tests/unit/test_models.py.
"""

URL = "https://example.com/some/path"


def _create(client) -> dict:
    return client.post("/api/links", json={"url": URL}).json()


def assert_link_shape(body: dict) -> None:
    assert set(body) == {"code", "url", "clicks"}
    assert isinstance(body["code"], str) and body["code"]
    assert isinstance(body["url"], str)
    assert isinstance(body["clicks"], int)


def assert_error_shape(body: dict) -> None:
    assert set(body) == {"detail"}
    assert isinstance(body["detail"], str)


# --- POST /api/links --------------------------------------------------------

def test_create_returns_201_and_link_shape(client):
    r = client.post("/api/links", json={"url": URL})
    assert r.status_code == 201
    assert_link_shape(r.json())


def test_create_without_body_field_returns_422(client):
    r = client.post("/api/links", json={})
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], list)


# --- GET /api/links ---------------------------------------------------------

def test_list_empty_returns_200_and_empty_array(client):
    r = client.get("/api/links")
    assert r.status_code == 200
    assert r.json() == []


def test_list_returns_200_and_array_of_link_shapes(client):
    _create(client)
    _create(client)
    r = client.get("/api/links")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list) and len(body) == 2
    for item in body:
        assert_link_shape(item)


# --- GET /api/links/{code}/stats --------------------------------------------

def test_stats_returns_200_and_link_shape(client):
    code = _create(client)["code"]
    r = client.get(f"/api/links/{code}/stats")
    assert r.status_code == 200
    assert_link_shape(r.json())


def test_stats_unknown_code_returns_404_and_error_shape(client):
    r = client.get("/api/links/nope12/stats")
    assert r.status_code == 404
    assert_error_shape(r.json())


# --- GET /{code} ------------------------------------------------------------

def test_follow_returns_307_with_location_header(client):
    code = _create(client)["code"]
    r = client.get(f"/{code}")
    assert r.status_code == 307
    assert r.headers["location"]


def test_follow_unknown_code_returns_404_and_error_shape(client):
    r = client.get("/nope12")
    assert r.status_code == 404
    assert_error_shape(r.json())
