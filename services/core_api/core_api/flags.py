"""Feature flag lookups, cached 30 s (CONTRACTS.md §6 ``flags:cache``).

The flag map is cached in the Django cache and mirrored to the Redis hash ``flags:cache`` (30 s TTL)
so ingest-ml and realtime can read flags without calling core-api.
"""

from __future__ import annotations

import logging

import redis
from django.core.cache import cache

from .redis_client import get_redis

log = logging.getLogger(__name__)

CACHE_KEY = "flags:all:v1"
REDIS_KEY = "flags:cache"
TTL_SECONDS = 30


def _load() -> dict[str, dict[str, bool]]:
    from .models import FeatureFlag

    rows = FeatureFlag.objects.values_list("name", "enabled", "public")
    return {name: {"enabled": enabled, "public": public} for name, enabled, public in rows}


def _mirror_to_redis(flags: dict[str, dict[str, bool]]) -> None:
    if not flags:
        return
    try:
        r = get_redis()
        pipe = r.pipeline()
        pipe.delete(REDIS_KEY)
        pipe.hset(REDIS_KEY, mapping={k: "1" if v["enabled"] else "0" for k, v in flags.items()})
        pipe.expire(REDIS_KEY, TTL_SECONDS)
        pipe.execute()
    except redis.RedisError:
        log.warning("flags mirror to redis failed")


def all_flags() -> dict[str, dict[str, bool]]:
    flags = cache.get(CACHE_KEY)
    if flags is None:
        flags = _load()
        cache.set(CACHE_KEY, flags, TTL_SECONDS)
        _mirror_to_redis(flags)
    return flags


def is_enabled(name: str, default: bool = False) -> bool:
    flag = all_flags().get(name)
    return flag["enabled"] if flag is not None else default


def public_flags() -> dict[str, bool]:
    return {k: v["enabled"] for k, v in all_flags().items() if v["public"]}


def invalidate() -> None:
    cache.delete(CACHE_KEY)
