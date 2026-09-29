"""Shared Redis client for live state (`np:*`, `last:*`) and streams (CONTRACTS.md §6).

Tests swap the client for fakeredis via ``set_client``.
"""

from __future__ import annotations

import redis
from django.conf import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
        )
    return _client


def set_client(client: redis.Redis | None) -> None:
    global _client
    _client = client
