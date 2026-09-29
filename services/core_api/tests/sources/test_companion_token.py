"""POST /api/v1/sources/companion/token proxies to ingest-ml (ADR-0006, JNG-01-13)."""

import json

import httpx
import pytest
import respx

pytestmark = pytest.mark.django_db

URL = "/api/v1/sources/companion/token"


@pytest.fixture
def ingest(settings):
    settings.INGEST_INTERNAL_URL = "http://ingest-ml.test:8001"
    settings.SERVICE_TOKEN = "svc-token"
    with respx.mock(base_url="http://ingest-ml.test:8001", assert_all_called=False) as mock:
        yield mock


def test_issues_token_once(auth_api, user, ingest):
    route = ingest.post("/internal/scrobble-tokens").mock(
        return_value=httpx.Response(201, json={"token": "jng_secret"})
    )
    r = auth_api.post(URL)
    assert r.status_code == 201
    assert r.json() == {"token": "jng_secret"}
    assert r["Cache-Control"] == "no-store"
    sent = route.calls.last.request
    assert sent.headers["X-Service-Token"] == "svc-token"
    assert json.loads(sent.content) == {"user_id": str(user.pk)}


@pytest.mark.parametrize(
    "response",
    [httpx.Response(500), httpx.Response(200, json={}), httpx.Response(200, text="not json")],
)
def test_upstream_errors_map_to_502(auth_api, ingest, response):
    ingest.post("/internal/scrobble-tokens").mock(return_value=response)
    r = auth_api.post(URL)
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "UPSTREAM_UNAVAILABLE"


def test_upstream_unreachable(auth_api, ingest):
    ingest.post("/internal/scrobble-tokens").mock(side_effect=httpx.ConnectError("down"))
    assert auth_api.post(URL).status_code == 502


def test_unauthenticated(api, ingest):
    assert api.post(URL).status_code == 401


def test_rate_limited(auth_api, ingest):
    ingest.post("/internal/scrobble-tokens").mock(
        return_value=httpx.Response(201, json={"token": "t"})
    )
    for _ in range(10):
        assert auth_api.post(URL).status_code == 201
    assert auth_api.post(URL).status_code == 429
