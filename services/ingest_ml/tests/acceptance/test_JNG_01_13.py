"""Acceptance: JNG-01-13 push endpoint (pytest-bdd).

Steps are sync (pytest-bdd), so each scenario drives the ASGI app on its own event loop.
"""

import asyncio
import time
from collections.abc import Coroutine, Iterator
from typing import Any, TypeVar

import httpx
import pytest
from pytest_bdd import given, scenarios, then, when

from ingest_ml.main import create_app
from ingest_ml.resources import Resources

from ..conftest import User, create_user, make_resources

scenarios("../features/ep01/JNG-01-13_push.feature")

T = TypeVar("T")


class World:
    def __init__(self) -> None:
        self.runner = asyncio.Runner()
        self.res: Resources = self.run(make_resources())
        self.app = create_app(resources=self.res)
        self.user: User | None = None
        self.response: httpx.Response | None = None
        self.sent_at = 0.0

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        return self.runner.run(coro)

    async def post(self, path: str, json: Any, headers: dict[str, str]) -> httpx.Response:
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://ingest") as c:
            return await c.post(path, json=json, headers=headers)


@pytest.fixture
def world() -> Iterator[World]:
    w = World()
    yield w
    w.run(w.res.engine.dispose())
    w.runner.close()


YTM_TRACK = {
    "artist_name": "Arijit Singh - Topic",
    "track_name": 'Kesariya (From "Brahmastra")',
    "additional_info": {
        "music_service": "music.youtube.com",
        "origin_url": "https://music.youtube.com/watch?v=BddP6PYo2gs",
        "submission_client": "Jingle Companion",
        "duration": 268,
    },
}


@given("a user with a Jingle scrobble token")
def user_with_token(world: World) -> None:
    world.user = world.run(create_user(world.res.engine))


@when("the Companion sends playing_now for a YouTube Music track")
def companion_sends(world: World) -> None:
    assert world.user
    world.sent_at = time.time()
    world.response = world.run(
        world.post(
            "/ingest/1/submit-listens",
            {"listen_type": "playing_now", "payload": [{"track_metadata": YTM_TRACK}]},
            world.user.auth,
        )
    )
    assert world.response.status_code == 200, world.response.text


@then("np:{user} exists with platform YOUTUBE_MUSIC and observed_at within 2 s")
def np_is_live(world: World) -> None:
    assert world.user
    np = world.run(world.res.redis.hgetall(f"np:{world.user.id}"))
    assert np, "np:{user} missing"
    assert np["platform"] == "YOUTUBE_MUSIC"
    lag = abs(float(np["observed_at"]) - world.sent_at)
    assert lag < 2.0, f"observed_at is {lag:.2f} s from send time (threshold 2 s)"
    ttl = world.run(world.res.redis.ttl(f"np:{world.user.id}"))
    assert 0 < ttl <= 90


@when("a scrobbler sends playing_now with an unknown token")
def unknown_token(world: World) -> None:
    world.response = world.run(
        world.post(
            "/ingest/1/submit-listens",
            {"listen_type": "playing_now", "payload": [{"track_metadata": YTM_TRACK}]},
            {"Authorization": "Token jng_this-token-does-not-exist"},
        )
    )


@then("the response is 401 in ListenBrainz error format")
def is_401(world: World) -> None:
    assert world.response is not None
    assert world.response.status_code == 401
    body = world.response.json()
    assert body["code"] == 401 and isinstance(body["error"], str)


@then("nothing is written for the user")
def nothing_written(world: World) -> None:
    assert world.user
    keys = world.run(world.res.redis.keys("*"))
    assert [k for k in keys if not k.startswith(("rl:", b"rl:"))] == []
    assert world.run(world.res.mongo["listens"].count_documents({})) == 0
