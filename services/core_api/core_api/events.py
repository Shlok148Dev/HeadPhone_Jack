"""Domain events to realtime and workers via Redis Stream ``events:domain`` (CONTRACTS.md §6).

Entry fields: ``type`` (e.g. ``feed.invalidate``) and ``data`` (JSON payload). Publishing never
raises: a Redis outage must not fail the user's request.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis

from .redis_client import get_redis

log = logging.getLogger(__name__)

DOMAIN_STREAM = "events:domain"
STREAM_MAXLEN = 100_000


def publish(stream: str, type: str, payload: dict[str, Any]) -> str | None:  # noqa: A002
    """Append an event; returns the entry id, or ``None`` when Redis is unavailable."""
    try:
        return get_redis().xadd(
            stream,
            {"type": type, "data": json.dumps(payload, default=str)},
            maxlen=STREAM_MAXLEN,
            approximate=True,
        )
    except redis.RedisError:
        log.warning("event publish failed", extra={"stream": stream, "event_type": type})
        return None


def publish_domain(type: str, payload: dict[str, Any]) -> str | None:  # noqa: A002
    return publish(DOMAIN_STREAM, type, payload)
