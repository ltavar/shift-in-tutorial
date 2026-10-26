import pytest
from fastapi.testclient import TestClient

from snip.main import app
from snip.store import store


@pytest.fixture(autouse=True)
def clean_store():
    store._links.clear()
    yield
    store._links.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, follow_redirects=False)
