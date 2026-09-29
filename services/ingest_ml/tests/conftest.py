"""Offline test harness: SQLite (create_all), fakeredis (with Lua), mongomock-motor, respx."""

import os

os.environ.setdefault("JINGLE_ENV", "test")
os.environ.setdefault("SERVICE_TOKEN", "test-service-token")

from collections.abc import AsyncIterator, Awaitable, Callable  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from typing import Any  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import fakeredis  # noqa: E402
import httpx  # noqa: E402
import pytest  # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncEngine  # noqa: E402

from ingest_ml.auth import hash_token, mint_token  # noqa: E402
from ingest_ml.db import make_engine, metadata, now, scrobble_tokens, users  # noqa: E402
from ingest_ml.main import create_app  # noqa: E402
from ingest_ml.resources import Resources  # noqa: E402
from ingest_ml.settings import Settings  # noqa: E402

SERVICE_TOKEN = "test-service-token"  # noqa: S105


async def make_resources(settings: Settings | None = None) -> Resources:
    engine = make_engine("sqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    mongo = AsyncMongoMockClient(tz_aware=True)["jingle"]
    cfg = settings or Settings(jingle_env="test", service_token=SERVICE_TOKEN)
    return Resources.build(cfg, engine=engine, redis=redis, mongo=mongo)


@dataclass
class User:
    id: UUID
    token: str
    token_id: UUID

    @property
    def auth(self) -> dict[str, str]:
        return {"Authorization": f"Token {self.token}"}


async def create_user(engine: AsyncEngine) -> User:
    uid, tid, token = uuid4(), uuid4(), mint_token()
    ts = now()
    async with engine.begin() as conn:
        await conn.execute(users.insert().values(id=uid, username=f"user_{uid.hex[:8]}"))
        await conn.execute(
            scrobble_tokens.insert().values(
                id=tid,
                user_id=uid,
                token_sha256=hash_token(token),
                label="Jingle Companion",
                created_at=ts,
                updated_at=ts,
            )
        )
    return User(uid, token, tid)


@pytest.fixture
async def res() -> AsyncIterator[Resources]:
    r = await make_resources()
    yield r
    await r.http.aclose()
    await r.engine.dispose()


@pytest.fixture
async def client(res: Resources) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(resources=res)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://ingest") as c:
        yield c


@pytest.fixture
async def user(res: Resources) -> User:
    return await create_user(res.engine)


UserFactory = Callable[[], Awaitable[User]]


@pytest.fixture
def user_factory(res: Resources) -> UserFactory:
    async def _make() -> User:
        return await create_user(res.engine)

    return _make


def track(
    artist: str = "Arijit Singh",
    title: str = "Kesariya",
    **info: Any,
) -> dict[str, Any]:
    return {"artist_name": artist, "track_name": title, "additional_info": info}
