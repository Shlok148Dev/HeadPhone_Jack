"""Polling for routes that cannot push (Technical Bible 2.3, 7.2).

A Redis sorted set ``poll:next`` holds each route's next due time. A periodic job (Celery beat in
core-api → ``POST /internal/poll/due``) polls what is due, records plays through the shared path,
and reschedules with ±20 % jitter. Now-playing is polled at the source's live interval; recent
plays every 5 minutes. When a budget is empty the poll is skipped and cards keep their cached
state with its true time (NFR-AVAIL-03).
"""

import logging
import random
import time
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from jingle_common.enums import EventKind, Platform, SourceKind, SourceStatus

from .adapters.base import NotSupported
from .adapters.common import AdapterError, BudgetExhausted, RateLimited, ReauthRequired
from .orchestrator import POLL_ZSET, Orchestrator
from .record import record_plays
from .sources_store import (
    ensure_platform_connection,
    get_source_by_id,
    list_sources,
    save_source,
    update_source,
)

log = logging.getLogger(__name__)

POLLED_KINDS = [
    SourceKind.SPOTIFY,
    SourceKind.LISTENBRAINZ,
    SourceKind.LASTFM,
    SourceKind.APPLE_MUSIC,
]
LIVE_INTERVAL = {SourceKind.SPOTIFY: 20, SourceKind.LISTENBRAINZ: 30, SourceKind.LASTFM: 60}
RECENT_INTERVAL = {SourceKind.APPLE_MUSIC: 600}
DEFAULT_RECENT_INTERVAL = 300
IDLE_RECENT_INTERVAL = 900  # nobody watching: recents only, every 15 min (Tech Bible 2.3)
BACKFILL = timedelta(days=14)
ACTIVE = [SourceStatus.CONNECTED, SourceStatus.PENDING_FIRST_PLAY]


def _jitter(seconds: float) -> float:
    return seconds * random.uniform(0.8, 1.2)  # noqa: S311 - scheduling jitter


async def sync_schedule(orch: Orchestrator) -> int:
    """Add active routes missing from the schedule (e.g. after a Redis restart)."""
    redis = orch.res.redis
    added = 0
    for src in await list_sources(orch.res.engine, POLLED_KINDS, ACTIVE):
        if await redis.zscore(POLL_ZSET, str(src.id)) is None:
            await redis.zadd(POLL_ZSET, {str(src.id): 0})
            added += 1
    return added


async def poll_due(
    orch: Orchestrator, flags: Mapping[str, bool], limit: int = 50, now_ts: float | None = None
) -> dict[str, int]:
    now_ts = now_ts or time.time()
    counts = {"polled": 0, "live": 0, "listens": 0, "skipped": 0, "reauth": 0, "errors": 0}
    await sync_schedule(orch)
    due = await orch.res.redis.zrangebyscore(POLL_ZSET, "-inf", now_ts, start=0, num=limit)
    for raw in due:
        member = raw.decode() if isinstance(raw, bytes) else str(raw)
        next_in = await _poll_one(orch, member, flags, now_ts, counts)
        if next_in is None:
            await orch.res.redis.zrem(POLL_ZSET, member)
        else:
            await orch.res.redis.zadd(POLL_ZSET, {member: now_ts + _jitter(next_in)})
    return counts


async def _poll_one(
    orch: Orchestrator,
    member: Any,
    flags: Mapping[str, bool],
    now_ts: float,
    counts: dict[str, int],
) -> float | None:
    from uuid import UUID

    src = await get_source_by_id(orch.res.engine, UUID(str(member)))
    if src is None or src.status not in ACTIVE:
        return None
    adapter = orch.adapter(src.kind, flags)
    if adapter is None:
        counts["skipped"] += 1
        return None  # flag off or not configured: drop from schedule until re-linked
    # Adaptive polling: live only while the user or a friend has Jingle open (realtime sets
    # presence:{u} for the user and watched:{u} for each of their online friends' friends).
    uid = str(src.user_id)
    active = bool(await orch.res.redis.exists(f"presence:{uid}", f"watched:{uid}"))
    live_every = LIVE_INTERVAL.get(src.kind) if active else None
    recent_every = RECENT_INTERVAL.get(
        src.kind, DEFAULT_RECENT_INTERVAL if active else IDLE_RECENT_INTERVAL
    )
    meta = dict(src.meta)
    platform = Platform(meta.get("platform", "UNKNOWN"))
    now = datetime.fromtimestamp(now_ts, UTC)
    route = adapter  # has kind/caps
    via = adapter.via
    catalog_writes = src.kind is not SourceKind.SPOTIFY  # Spotify API data stays display-only
    counts["polled"] += 1
    try:
        refreshed = await adapter.refresh(src)
        if refreshed.token_ciphertext != src.token_ciphertext:
            src = await save_source(orch.res.engine, refreshed)
        if live_every and adapter.caps.live:
            play = await adapter.poll_now(src, now)
            if play is not None:
                await record_plays(
                    orch.res,
                    src.user_id,
                    [play],
                    kind=EventKind.NOW_PLAYING,
                    route=route,
                    via=via,
                    received_at=now,
                    catalog_writes=catalog_writes,
                )
                counts["live"] += 1
        if now_ts - float(meta.get("recent_polled_at", 0)) >= recent_every:
            cursor = float(meta.get("recent_cursor", 0)) or (now - BACKFILL).timestamp()
            plays = await adapter.recent_plays(src, datetime.fromtimestamp(cursor, UTC))
            if plays:
                written = await record_plays(
                    orch.res,
                    src.user_id,
                    plays,
                    kind=EventKind.LISTEN,
                    route=route,
                    via=via,
                    received_at=now,
                    allow_remote=False,
                    catalog_writes=catalog_writes,
                )
                counts["listens"] += len(written)
                meta["recent_cursor"] = max(p.played_at.timestamp() for p in plays)
            meta["recent_polled_at"] = now_ts
            if "seen_ids" in src.meta:
                meta["seen_ids"] = src.meta["seen_ids"]
        meta.pop("reason", None)
        await update_source(orch.res.engine, src.id, meta=meta, ok=True)
    except ReauthRequired as exc:
        counts["reauth"] += 1
        # Spotify 403 at poll time = removed from the allowlist: stop quietly (BR-15).
        status = (
            SourceStatus.DISABLED
            if exc.reason == "http_403" and src.kind is SourceKind.SPOTIFY
            else SourceStatus.NEEDS_REAUTH
        )
        await update_source(
            orch.res.engine, src.id, status=status, meta={**meta, "reason": exc.reason}
        )
        if status is SourceStatus.NEEDS_REAUTH:
            await ensure_platform_connection(
                orch.res.engine, src.user_id, platform, SourceStatus.NEEDS_REAUTH
            )
        return None
    except RateLimited as exc:
        counts["skipped"] += 1
        return max(exc.retry_after, float(live_every or recent_every))
    except BudgetExhausted:
        counts["skipped"] += 1
    except NotSupported:
        counts["skipped"] += 1
    except AdapterError as exc:
        counts["errors"] += 1
        log.warning("poll failed for a %s route: %s", src.kind.value, exc)
        return float(live_every or recent_every) * 3
    return float(live_every or recent_every)
