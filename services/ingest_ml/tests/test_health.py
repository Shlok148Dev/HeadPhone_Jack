from fastapi.testclient import TestClient

from ingest_ml.main import app


def test_healthz() -> None:
    assert TestClient(app).get("/healthz").json() == {"status": "ok"}
