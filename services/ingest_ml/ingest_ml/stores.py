"""Redis and MongoDB accessors (CONTRACTS.md §2, §6; ADR-0004)."""

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import CollectionInvalid, OperationFailure
from redis.asyncio import Redis

log = logging.getLogger(__name__)

LISTENS = "listens"
# 13 months + a margin (395.7 days), Tech Bible 3.3 / SRS 8.2 retention
LISTENS_TTL_SECONDS = 34_187_400
NAMESPACE_EXISTS = 48

MongoDatabase = AsyncIOMotorDatabase[dict[str, Any]]


def make_redis(url: str) -> "Redis":
    return Redis.from_url(url, decode_responses=True)


def make_mongo(url: str) -> MongoDatabase:
    client: AsyncIOMotorClient[dict[str, Any]] = AsyncIOMotorClient(url, tz_aware=True)
    return client.get_default_database("jingle")


async def ensure_mongo_indexes(db: MongoDatabase) -> None:
    """Create the ``listens`` time-series collection and its indexes. Idempotent."""
    existing = await db.list_collection_names()
    if LISTENS not in existing:
        try:
            await db.create_collection(
                LISTENS,
                timeseries={
                    "timeField": "played_at",
                    "metaField": "meta",
                    "granularity": "minutes",
                },
                expireAfterSeconds=LISTENS_TTL_SECONDS,
            )
        except CollectionInvalid:
            pass  # created concurrently by another replica
        except OperationFailure as exc:
            if exc.code != NAMESPACE_EXISTS:
                raise
    await db[LISTENS].create_index([("meta.user_id", 1), ("played_at", -1)], name="user_played_at")
    await db[LISTENS].create_index([("recording_id", 1)], name="recording_id")
    log.info("mongo listens collection ready")
