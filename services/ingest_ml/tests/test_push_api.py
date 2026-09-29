"""ListenBrainz wire compatibility of /ingest/1/* (JNG-01-13, ADR-0003)."""

import json
import time
from datetime import UTC, datetime, timedelta

import httpx
import time_machine
from sqlalchemy import select

from ingest_ml.db import linked_sources, platform_connections, recording_links, scrobble_tokens
from ingest_ml.push.service import STREAM
from ingest_ml.resources import Resources
from ingest_ml.settings import Settings

from .conftest import User, make_resources, track

YTM = {
    "music_service": "music.youtube.com",
    "origin_url": "https://music.youtube.com/watch?v=abc123",
}


async def _submit(client: httpx.AsyncClient, user: User, body: object) -> httpx.Response:
    return await client.post("/ingest/1/submit-listens", json=body, headers=user.auth)


async def test_validate_token_valid(client: httpx.AsyncClient, user: User) -> None:
    r = await client.get("/ingest/1/validate-token", headers=user.auth)
    assert r.status_code == 200
    assert r.json() == {
        "code": 200,
        "message": "Token valid.",
        "valid": True,
        "user_name": str(user.id),
    }


async def test_validate_token_invalid_and_missing(client: httpx.AsyncClient) -> None:
    r = await client.get("/ingest/1/validate-token", headers={"Authorization": "Token nope"})
    assert r.status_code == 200
    assert r.json() == {"code": 200, "message": "Token invalid.", "valid": False}
    r = await client.get("/ingest/1/validate-token")
    assert r.status_code == 400
    assert r.json()["code"] == 400 and "error" in r.json()


async def test_submit_single_ok_shape_and_headers(
    client: httpx.AsyncClient, user: User, res: Resources
) -> None:
    body = {
        "listen_type": "single",
        "payload": [{"listened_at": int(time.time()) - 200, "track_metadata": track(**YTM)}],
    }
    r = await _submit(client, user, body)
    assert r.status_code == 200, r.text
    assert r.json() == {"status": "ok"}
    for h in ("X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset-In"):
        assert h in r.headers
    assert r.headers["X-RateLimit-Limit"] == "60"
    assert r.headers["x-request-id"]
    async with res.engine.connect() as conn:
        tok = (await conn.execute(select(scrobble_tokens))).mappings().one()
        assert tok["last_used_at"] is not None
        conn_row = (await conn.execute(select(platform_connections))).mappings().one()
        assert conn_row["platform"] == "YOUTUBE_MUSIC"
        assert conn_row["status"] == "CONNECTED"
        assert conn_row["first_play_at"] is not None
        src = (await conn.execute(select(linked_sources))).mappings().one()
        assert src["kind"] == "COMPANION" and src["status"] == "CONNECTED"
        link = (await conn.execute(select(recording_links))).mappings().one()
        assert link["platform"] == "YOUTUBE_MUSIC" and link["external_id"] == "abc123"


async def test_invalid_token_401_writes_nothing(client: httpx.AsyncClient, res: Resources) -> None:
    body = {"listen_type": "playing_now", "payload": [{"track_metadata": track(**YTM)}]}
    for header in ({"Authorization": "Token jng_wrong"}, {"Authorization": "Bearer x"}, {}):
        r = await client.post("/ingest/1/submit-listens", json=body, headers=header)
        assert r.status_code == 401
        assert r.json()["code"] == 401 and r.json()["error"]
    assert await res.redis.keys("*") == []
    assert await res.mongo["listens"].count_documents({}) == 0
    async with res.engine.connect() as conn:
        assert (await conn.execute(select(platform_connections))).first() is None


async def test_revoked_token_rejected(
    client: httpx.AsyncClient, user: User, res: Resources
) -> None:
    async with res.engine.begin() as conn:
        await conn.execute(scrobble_tokens.update().values(revoked_at=datetime.now(UTC)))
    r = await client.get("/ingest/1/validate-token", headers=user.auth)
    assert r.json()["valid"] is False


async def test_validation_errors_are_lb_400(client: httpx.AsyncClient, user: User) -> None:
    now = int(time.time())
    bad = [
        {"listen_type": "bogus", "payload": [{"track_metadata": track()}]},
        {"listen_type": "single", "payload": []},
        {"listen_type": "single", "payload": [{"listened_at": now, "track_metadata": track()}] * 2},
        {
            "listen_type": "playing_now",
            "payload": [{"listened_at": now, "track_metadata": track()}],
        },
        {"listen_type": "import", "payload": [{"track_metadata": track()}]},
        {
            "listen_type": "import",
            "payload": [{"listened_at": now, "track_metadata": track()}] * 1001,
        },
        {
            "listen_type": "single",
            "payload": [
                {"listened_at": now, "track_metadata": {"artist_name": " ", "track_name": "x"}}
            ],
        },
    ]
    for body in bad:
        r = await _submit(client, user, body)
        assert r.status_code == 400, body["listen_type"]
        assert r.json()["code"] == 400 and isinstance(r.json()["error"], str)
    r = await client.post("/ingest/1/submit-listens", content=b"{not json", headers=user.auth)
    assert r.status_code == 400 and r.json()["error"] == "Cannot parse JSON document."


async def test_future_timestamp_rejected(
    client: httpx.AsyncClient, user: User, res: Resources
) -> None:
    future = int(time.time()) + 6 * 60
    body = {
        "listen_type": "single",
        "payload": [{"listened_at": future, "track_metadata": track()}],
    }
    r = await _submit(client, user, body)
    assert r.status_code == 400
    assert "future" in r.json()["error"]
    assert await res.mongo["listens"].count_documents({}) == 0
    # 4 minutes ahead (client clock skew) is tolerated
    body["payload"][0]["listened_at"] = int(time.time()) + 4 * 60  # type: ignore[index]
    assert (await _submit(client, user, body)).status_code == 200


async def test_playing_now_writes_np_with_ttl_and_stream(
    client: httpx.AsyncClient, user: User, res: Resources
) -> None:
    before = time.time()
    r = await client.post(
        "/ingest/1/playing-now", json=track(**YTM, duration=215), headers=user.auth
    )
    assert r.status_code == 200, r.text
    np = await res.redis.hgetall(f"np:{user.id}")
    assert np["platform"] == "YOUTUBE_MUSIC" and np["via"] == "COMPANION"
    assert before - 1 <= float(np["observed_at"]) <= time.time() + 1
    ttl = await res.redis.ttl(f"np:{user.id}")
    assert 0 < ttl <= 90
    event = json.loads(np["event"])
    assert event["kind"] == "NOW_PLAYING" and event["raw"]["duration_ms"] == 215000
    assert event["trainable"] is True
    assert await res.redis.exists(f"last:{user.id}")
    entries = await res.redis.xrange(STREAM)
    assert len(entries) == 1
    assert json.loads(entries[0][1]["data"])["event_id"] == event["event_id"]
    # playing_now is not a listen
    assert await res.mongo["listens"].count_documents({}) == 0


async def test_playing_now_accepts_wrapped_track_metadata(
    client: httpx.AsyncClient, user: User, res: Resources
) -> None:
    r = await client.post(
        "/ingest/1/playing-now",
        json={"track_metadata": track(music_service="spotify.com")},
        headers=user.auth,
    )
    assert r.status_code == 200
    assert (await res.redis.hget(f"np:{user.id}", "platform")) == "SPOTIFY"


async def test_listen_inserts_mongo_and_last_only_if_newer(
    client: httpx.AsyncClient, user: User, res: Resources
) -> None:
    t0 = int(time.time())
    newer = {
        "listen_type": "single",
        "payload": [{"listened_at": t0 - 60, "track_metadata": track(title="Tum Hi Ho")}],
    }
    older = {
        "listen_type": "single",
        "payload": [{"listened_at": t0 - 3600, "track_metadata": track(title="Channa Mereya")}],
    }
    assert (await _submit(client, user, newer)).status_code == 200
    assert (await _submit(client, user, older)).status_code == 200
    docs = await res.mongo["listens"].find({}).to_list(None)
    assert len(docs) == 2
    doc = next(d for d in docs if d["raw"]["title"] == "Tum Hi Ho")
    assert doc["meta"] == {"user_id": str(user.id), "platform": "UNKNOWN", "via": "COMPANION"}
    assert doc["trainable"] is True and doc["recording_id"] and doc["event_id"]
    last = await res.redis.hgetall(f"last:{user.id}")
    assert json.loads(last["event"])["raw"]["title"] == "Tum Hi Ho"
    # Recent time for a finished listen is its play time, not receive time
    assert abs(float(last["observed_at"]) - (t0 - 60)) < 2
    assert await res.redis.ttl(f"last:{user.id}") == -1
    assert not await res.redis.exists(f"np:{user.id}")
    assert len(await res.redis.xrange(STREAM)) == 2


async def test_import_many_listens(client: httpx.AsyncClient, user: User, res: Resources) -> None:
    t0 = int(time.time()) - 86400
    payload = [
        {
            "listened_at": t0 + i * 240,
            "track_metadata": track(title=f"Song {i}", music_service_name="Apple Music"),
        }
        for i in range(25)
    ]
    r = await _submit(client, user, {"listen_type": "import", "payload": payload})
    assert r.status_code == 200
    assert await res.mongo["listens"].count_documents({}) == 25
    last = json.loads(await res.redis.hget(f"last:{user.id}", "event"))
    assert last["raw"]["title"] == "Song 24" and last["platform"] == "APPLE_MUSIC"
    async with res.engine.connect() as conn:
        row = (await conn.execute(select(platform_connections))).mappings().one()
    first = row["first_play_at"]
    first = first if first.tzinfo else first.replace(tzinfo=UTC)
    assert abs(first.timestamp() - t0) < 2


async def test_listened_at_defaults_to_now_for_single(
    client: httpx.AsyncClient, user: User, res: Resources
) -> None:
    with time_machine.travel(datetime(2026, 9, 29, 10, 15, tzinfo=UTC), tick=False):
        r = await _submit(
            client, user, {"listen_type": "single", "payload": [{"track_metadata": track()}]}
        )
    assert r.status_code == 200
    doc = await res.mongo["listens"].find_one({})
    played = doc["played_at"]
    played = played if played.tzinfo else played.replace(tzinfo=UTC)
    assert played == datetime(2026, 9, 29, 10, 15, tzinfo=UTC)


async def test_rate_limit_429(user: User) -> None:
    res = await make_resources(Settings(jingle_env="test", push_rate_limit_per_minute=3))
    from ingest_ml.auth import hash_token
    from ingest_ml.db import now, scrobble_tokens, users

    async with res.engine.begin() as conn:
        await conn.execute(users.insert().values(id=user.id))
        await conn.execute(
            scrobble_tokens.insert().values(
                id=user.token_id,
                user_id=user.id,
                token_sha256=hash_token(user.token),
                label="x",
                created_at=now(),
                updated_at=now(),
            )
        )
    from ingest_ml.main import create_app

    app = create_app(resources=res)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        codes = []
        for _ in range(5):
            r = await c.post("/ingest/1/playing-now", json=track(), headers=user.auth)
            codes.append(r.status_code)
        assert codes[:3] == [200, 200, 200]
        assert codes[3] == 429
        assert r.json() == {"code": 429, "error": "Rate limit exceeded."}
        assert r.headers["X-RateLimit-Remaining"] == "0"
        assert int(r.headers["Retry-After"]) >= 1


async def test_disabled_connection_stays_disabled(
    client: httpx.AsyncClient, user: User, res: Resources
) -> None:
    await client.post("/ingest/1/playing-now", json=track(**YTM), headers=user.auth)
    async with res.engine.begin() as conn:
        await conn.execute(platform_connections.update().values(status="DISABLED"))
    await client.post("/ingest/1/playing-now", json=track(**YTM), headers=user.auth)
    async with res.engine.connect() as conn:
        row = (await conn.execute(select(platform_connections))).mappings().one()
    assert row["status"] == "DISABLED"


async def test_pending_connection_flips_to_connected(
    client: httpx.AsyncClient, user: User, res: Resources
) -> None:
    from uuid import uuid4

    from ingest_ml.db import now

    async with res.engine.begin() as conn:
        await conn.execute(
            platform_connections.insert().values(
                id=uuid4(),
                user_id=user.id,
                platform="SPOTIFY",
                status="PENDING_FIRST_PLAY",
                created_at=now(),
                updated_at=now(),
            )
        )
    body = {
        "listen_type": "single",
        "payload": [
            {
                "listened_at": int(time.time()) - 100,
                "track_metadata": track(
                    music_service="spotify.com",
                    spotify_id="https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh",
                ),
            }
        ],
    }
    assert (await _submit(client, user, body)).status_code == 200
    async with res.engine.connect() as conn:
        row = (await conn.execute(select(platform_connections))).mappings().one()
        link = (await conn.execute(select(recording_links))).mappings().one()
    assert row["status"] == "CONNECTED" and row["first_play_at"] is not None
    assert row["last_signal_at"] is not None
    assert link["external_id"] == "4iV5W9uYEdYUVa79Axb7Rh"


async def test_unsafe_origin_url_not_stored(
    client: httpx.AsyncClient, user: User, res: Resources
) -> None:
    info = {"music_service": "music.youtube.com", "origin_url": "javascript:alert(1)"}
    await client.post("/ingest/1/playing-now", json=track(**info), headers=user.auth)
    async with res.engine.connect() as conn:
        assert (await conn.execute(select(recording_links))).first() is None


async def test_timestamps_older_than_now_accepted_for_import(
    client: httpx.AsyncClient, user: User
) -> None:
    old = int((datetime.now(UTC) - timedelta(days=300)).timestamp())
    body = {"listen_type": "import", "payload": [{"listened_at": old, "track_metadata": track()}]}
    assert (await _submit(client, user, body)).status_code == 200
