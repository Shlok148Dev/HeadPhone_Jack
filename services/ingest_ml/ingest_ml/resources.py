"""Process-wide clients, built once in the app lifespan (or injected by tests)."""

import logging
from dataclasses import dataclass

import httpx
from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from .db import make_engine
from .identity.musicbrainz import MusicBrainzClient
from .identity.resolver import IdentityResolver
from .ratelimit import TokenBucket
from .settings import Settings
from .stores import MongoDatabase, make_mongo, make_redis

log = logging.getLogger(__name__)


@dataclass
class Resources:
    settings: Settings
    engine: AsyncEngine
    redis: "Redis"
    mongo: MongoDatabase
    http: httpx.AsyncClient
    resolver: IdentityResolver
    push_bucket: TokenBucket  # requests per user per minute
    listen_bucket: TokenBucket  # listens per user per hour
    auth_fail_bucket: TokenBucket  # failed auth per client IP per minute
    mb_user_bucket: TokenBucket  # MusicBrainz lookups per user per minute

    @classmethod
    def build(
        cls,
        settings: Settings,
        *,
        engine: AsyncEngine | None = None,
        redis: "Redis | None" = None,
        mongo: MongoDatabase | None = None,
        http: httpx.AsyncClient | None = None,
    ) -> "Resources":
        engine = engine or make_engine(settings.database_url)
        redis = redis if redis is not None else make_redis(settings.redis_url)
        mongo = mongo if mongo is not None else make_mongo(settings.mongo_url)
        http = http or httpx.AsyncClient(follow_redirects=False)
        mb: MusicBrainzClient | None = None
        if settings.musicbrainz_active:
            mb = MusicBrainzClient(
                http,
                redis,
                user_agent=settings.musicbrainz_ua,
                base_url=settings.musicbrainz_api_url,
            )
        else:
            log.info("musicbrainz lookups disabled (no MUSICBRAINZ_CONTACT, demo mode or tests)")
        return cls(
            settings=settings,
            engine=engine,
            redis=redis,
            mongo=mongo,
            http=http,
            resolver=IdentityResolver(engine, redis, mb),
            push_bucket=TokenBucket(redis, settings.push_rate_limit_per_minute, 60.0),
            listen_bucket=TokenBucket(redis, settings.push_listen_limit_per_hour, 3600.0),
            auth_fail_bucket=TokenBucket(redis, settings.push_auth_fail_limit_per_minute, 60.0),
            mb_user_bucket=TokenBucket(redis, settings.musicbrainz_user_lookups_per_minute, 60.0),
        )

    async def close(self) -> None:
        await self.http.aclose()
        await self.redis.aclose()
        await self.engine.dispose()
        self.mongo.client.close()


def get_resources(request: Request) -> Resources:
    res: Resources = request.app.state.resources
    return res
