import pytest


@pytest.mark.django_db
def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["db"] == "ok"
    assert r["X-Request-ID"]


def test_ping_and_error_envelope(api):
    assert api.get("/api/v1/ping").json()["ok"] is True
    r = api.get("/api/v1/does-not-exist")
    assert r.status_code == 404
