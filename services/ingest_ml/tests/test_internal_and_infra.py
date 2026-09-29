"""Internal API, request ids, logging hygiene, stores, DB URL handling, rate-limit bucket."""

import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import fakeredis
import httpx
import pytest
from pymongo.errors import CollectionInvalid, OperationFailure
from sqlalchemy import select

from ingest_ml.auth import hash_token, parse_token_header
from ingest_ml.db import normalize_database_url, scrobble_tokens, users
from ingest_ml.ratelimit import TokenBucket
from ingest_ml.resources import Resources
from ingest_ml.settings import Settings
from ingest_ml.stores import LISTENS_TTL_SECONDS, ensure_mongo_indexes

from .conftest import SERVICE_TOKEN, User

SVC = {"X-Service-Token": SERVICE_TOKEN}


async def test_mint_and_revoke_scrobble_token(client: httpx.AsyncClient, res: Resources) -> None:
    uid = uuid4()
    async with res.engine.begin() as conn:
        await conn.execute(users.insert().values(id=uid))
    r = await client.post("/internal/scrobble-tokens", json={"user_id": str(uid)}, headers=SVC)
    assert r.status_code == 201
    body = r.json()
    token = body["token"]
    assert token.startswith("jng_") and len(token) > 40
    async with res.engine.connect() as conn:
        row = (await conn.execute(select(scrobble_tokens))).mappings().one()
    assert row["token_sha256"] == hash_token(token) and token not in str(dict(row))
    assert row["label"] == "Jingle Companion"
    auth = {"Authorization": f"Token {token}"}
    assert (await client.get("/ingest/1/validate-token", headers=auth)).json()["valid"] is True
    r = await client.delete(f"/internal/scrobble-tokens/{body['id']}", headers=SVC)
    assert r.status_code == 204
    assert (await client.get("/ingest/1/validate-token", headers=auth)).json()["valid"] is False
    r = await client.delete(f"/internal/scrobble-tokens/{uuid4()}", headers=SVC)
    assert r.status_code == 404 and r.json()["error"]["code"] == "TOKEN_NOT_FOUND"


async def test_mint_with_label_and_validation(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/internal/scrobble-tokens",
        json={"user_id": str(uuid4()), "label": "Pano Scrobbler"},
        headers=SVC,
    )
    assert r.status_code == 201  # SQLite does not enforce FKs; Postgres returns 404
    r = await client.post(
        "/internal/scrobble-tokens", json={"user_id": str(uuid4()), "label": "x" * 61}, headers=SVC
    )
    assert r.status_code == 422


async def test_mint_unknown_user_is_404(client: httpx.AsyncClient, res: Resources) -> None:
    async with res.engine.connect() as conn:
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        await conn.commit()
    r = await client.post("/internal/scrobble-tokens", json={"user_id": str(uuid4())}, headers=SVC)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "USER_NOT_FOUND"


async def test_internal_requires_service_token(client: httpx.AsyncClient) -> None:
    for headers in ({}, {"X-Service-Token": "wrong"}):
        r = await client.get("/internal/healthz", headers=headers)
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "SERVICE_TOKEN_INVALID"


async def test_internal_healthz(client: httpx.AsyncClient, res: Resources) -> None:
    r = await client.get("/internal/healthz", headers=SVC)
    assert r.status_code == 200
    assert r.json()["deps"] == {"postgres": "ok", "redis": "ok", "mongo": "ok"}
    assert r.json()["musicbrainz"] == "disabled"
    res.redis.ping = AsyncMock(side_effect=ConnectionError("down"))  # type: ignore[method-assign]
    r = await client.get("/internal/healthz", headers=SVC)
    assert r.status_code == 503 and r.json()["status"] == "degraded"


async def test_request_id_echoed_and_generated(client: httpx.AsyncClient) -> None:
    r = await client.get("/healthz", headers={"X-Request-ID": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123"
    r = await client.get("/healthz", headers={"X-Request-ID": "bad id\nx"})
    assert r.headers["x-request-id"] != "bad id\nx" and len(r.headers["x-request-id"]) == 32


async def test_tokens_never_logged(
    client: httpx.AsyncClient, user: User, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    await client.post(
        "/ingest/1/playing-now", json={"artist_name": "A", "track_name": "B"}, headers=user.auth
    )
    await client.post("/internal/scrobble-tokens", json={"user_id": str(user.id)}, headers=SVC)
    text = caplog.text
    assert user.token not in text and SERVICE_TOKEN not in text
    assert "jng_" not in text


def test_parse_token_header() -> None:
    assert parse_token_header("Token abc") == "abc"
    assert parse_token_header("token   abc ") == "abc"
    assert parse_token_header("Bearer abc") is None
    assert parse_token_header("Token ") is None
    assert parse_token_header("Token " + "x" * 201) is None
    assert parse_token_header(None) is None


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("postgres://u:p@h:5432/d", "postgresql+psycopg://u:p@h:5432/d"),
        ("postgresql://u:p@h/d", "postgresql+psycopg://u:p@h/d"),
        ("postgresql+psycopg://u@h/d", "postgresql+psycopg://u@h/d"),
        ("sqlite:///x.db", "sqlite+aiosqlite:///x.db"),
    ],
)
def test_normalize_database_url(url: str, expected: str) -> None:
    assert normalize_database_url(url) == expected


def test_make_engine_postgres_does_not_connect() -> None:
    from ingest_ml.db import make_engine

    eng = make_engine("postgres://u:p@localhost:1/d")
    assert eng.dialect.name == "postgresql" and eng.dialect.driver == "psycopg"


def _fake_db(existing: list[str], create_exc: Exception | None = None) -> Any:
    db = MagicMock()
    db.list_collection_names = AsyncMock(return_value=existing)
    db.create_collection = AsyncMock(side_effect=create_exc)
    coll = MagicMock()
    coll.create_index = AsyncMock()
    db.__getitem__.return_value = coll
    return db


async def test_ensure_mongo_indexes_creates_timeseries() -> None:
    db = _fake_db([])
    await ensure_mongo_indexes(db)
    kwargs = db.create_collection.call_args.kwargs
    assert db.create_collection.call_args.args == ("listens",)
    assert kwargs["timeseries"] == {
        "timeField": "played_at",
        "metaField": "meta",
        "granularity": "minutes",
    }
    assert kwargs["expireAfterSeconds"] == LISTENS_TTL_SECONDS == 34187400
    assert db["listens"].create_index.await_count == 2


async def test_ensure_mongo_indexes_idempotent() -> None:
    db = _fake_db(["listens"])
    await ensure_mongo_indexes(db)
    db.create_collection.assert_not_called()
    await ensure_mongo_indexes(_fake_db([], CollectionInvalid("exists")))
    await ensure_mongo_indexes(_fake_db([], OperationFailure("exists", code=48)))
    with pytest.raises(OperationFailure):
        await ensure_mongo_indexes(_fake_db([], OperationFailure("boom", code=2)))


async def test_token_bucket_refills() -> None:
    import time_machine

    redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    bucket = TokenBucket(redis, capacity=2, per_seconds=60)
    with time_machine.travel(1_900_000_000, tick=False) as tm:
        assert (await bucket.take("rl:t")).allowed
        r = await bucket.take("rl:t")
        assert r.allowed and r.remaining == 0
        r = await bucket.take("rl:t")
        assert not r.allowed and 29 <= r.retry_after <= 30.5
        assert r.headers()["X-RateLimit-Limit"] == "2"
        tm.shift(31)
        assert (await bucket.take("rl:t")).allowed
    with pytest.raises(ValueError):
        TokenBucket(redis, capacity=0, per_seconds=1)


def test_settings_musicbrainz_switch() -> None:
    tok = "s" * 40
    assert not Settings(jingle_env="test").musicbrainz_active
    assert not Settings(jingle_env="prod", service_token=tok).musicbrainz_active  # no contact → off
    assert Settings(jingle_env="prod", service_token=tok, musicbrainz_contact="a@b.c").musicbrainz_active
    assert not Settings(
        jingle_env="prod", service_token=tok, jingle_demo=True, musicbrainz_contact="a@b.c"
    ).musicbrainz_active
    assert Settings(
        jingle_env="test", musicbrainz_contact="a@b.c", musicbrainz_enabled=True
    ).musicbrainz_active
    assert Settings(musicbrainz_contact=" x ").musicbrainz_ua == "Jingle/0.1 ( x )"


async def test_app_lifespan_builds_and_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    from ingest_ml import main as main_mod
    from tests.conftest import make_resources

    res = await make_resources()
    closed: list[bool] = []

    async def fake_close() -> None:
        closed.append(True)

    res.close = fake_close  # type: ignore[method-assign]
    monkeypatch.setattr(main_mod.Resources, "build", classmethod(lambda cls, cfg: res))
    app = main_mod.create_app()
    async with app.router.lifespan_context(app):
        assert app.state.resources is res
    assert closed == [True]


def test_empty_env_values_use_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MUSICBRAINZ_ENABLED", "")
    monkeypatch.setenv("PUSH_RATE_LIMIT_PER_MINUTE", "")
    s = Settings()
    assert s.musicbrainz_enabled is None and s.push_rate_limit_per_minute == 60


def test_settings_refuse_weak_service_token_outside_dev() -> None:
    for bad in ("", "test-service-token", "dev-only-change-me-service-token-0000000000000", "short"):
        with pytest.raises(ValueError):
            Settings(jingle_env="prod", service_token=bad or "test-service-token")
    assert Settings(jingle_env="prod", service_token="s" * 40).service_token == "s" * 40
    assert Settings(jingle_env="local").service_token == "test-service-token"
