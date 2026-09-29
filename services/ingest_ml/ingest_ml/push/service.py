"""Turn a ListenBrainz submission into normalised events and write them (CONTRACTS.md §5, §6).

Every push to Jingle's endpoint is the COMPANION route (ADR-0003), whichever client sent it.
``observed_at`` is always the server receive time; the client's clock only sets ``played_at``.
"""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from jingle_common.enums import LIVE_MAX_AGE_SECONDS, EventKind, Platform, SourceKind, SourceStatus
from jingle_common.events import ListenEvent, RawTrack, default_trainable
from redis.typing import EncodableT, FieldT
from sqlalchemy import case, func
from sqlalchemy.ext.asyncio import AsyncEngine

from ..adapters.base import COMPANION_ROUTE, NowPlaying
from ..db import dialect_insert, linked_sources, now, platform_connections, recording_links
from ..identity.resolver import IdentityResolver, TrackInput
from ..resources import Resources
from ..stores import LISTENS
from .platform import external_id_from_url, infer_platform, safe_platform_url, spotify_url
from .schemas import Listen, Submission

log = logging.getLogger(__name__)

STREAM = "events:listen"
STREAM_MAXLEN = 100_000
MAX_FUTURE = timedelta(minutes=5)
NP_TTL_SECONDS = LIVE_MAX_AGE_SECONDS  # 90 s; refreshed by every playing_now (BR-01)


class PushRejected(Exception):
    """The submission violates an ingest rule; nothing was written."""


@dataclass
class _Prepared:
    listen: Listen
    platform: Platform
    played_at: datetime


def np_key(user_id: UUID) -> str:
    return f"np:{user_id}"


def last_key(user_id: UUID) -> str:
    return f"last:{user_id}"


def _prepare(sub: Submission, received_at: datetime) -> list[_Prepared]:
    out: list[_Prepared] = []
    for listen in sub.payload:
        ai = listen.track_metadata.additional_info
        if listen.listened_at is not None:
            played_at = datetime.fromtimestamp(listen.listened_at, UTC)
            if played_at > received_at + MAX_FUTURE:
                raise PushRejected("listened_at is more than 5 minutes in the future")
        else:
            played_at = received_at
        platform = infer_platform(ai.music_service, ai.origin_url, ai.music_service_name)
        out.append(_Prepared(listen, platform, played_at))
    return out


def _hash_fields(event: ListenEvent, observed_epoch: float) -> dict[FieldT, EncodableT]:
    return {
        "event": event.model_dump_json(),
        "observed_at": f"{observed_epoch:.3f}",
        "via": event.via.value,
        "platform": event.platform.value,
    }


async def _store_links(
    engine: AsyncEngine, recording_id: UUID, listen: Listen, platform: Platform
) -> None:
    ai = listen.track_metadata.additional_info
    links: dict[Platform, str] = {}
    if url := safe_platform_url(ai.origin_url, platform):
        links[platform] = url
    if url := spotify_url(ai.spotify_id):
        links[Platform.SPOTIFY] = url
    if not links:
        return
    async with engine.begin() as conn:
        for p, url in links.items():
            stmt = dialect_insert(conn, recording_links).values(
                recording_id=recording_id,
                platform=p.value,
                external_id=external_id_from_url(url, p),
                url=url,
                is_search=False,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["recording_id", "platform"],
                set_={"url": stmt.excluded.url, "external_id": stmt.excluded.external_id,
                      "is_search": False},
            )
            await conn.execute(stmt)


async def _upsert_sources(
    engine: AsyncEngine, user_id: UUID, first_play: dict[Platform, datetime], ts: datetime
) -> None:
    """First accepted submission flips PENDING_FIRST_PLAY → CONNECTED (ADR-0013..0016)."""
    async with engine.begin() as conn:
        for platform, played in first_play.items():
            if platform is Platform.UNKNOWN:
                continue
            t = platform_connections
            stmt = dialect_insert(conn, t).values(
                id=uuid4(), user_id=user_id, platform=platform.value,
                status=SourceStatus.CONNECTED.value, first_play_at=played,
                last_signal_at=ts, created_at=ts, updated_at=ts,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["user_id", "platform"],
                set_={
                    # a user-disabled connection stays disabled
                    "status": case(
                        (t.c.status == SourceStatus.DISABLED.value, t.c.status),
                        else_=SourceStatus.CONNECTED.value,
                    ),
                    "first_play_at": func.coalesce(t.c.first_play_at, stmt.excluded.first_play_at),
                    "last_signal_at": stmt.excluded.last_signal_at,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            await conn.execute(stmt)
        ls = linked_sources
        stmt = dialect_insert(conn, ls).values(
            id=uuid4(), user_id=user_id, kind=SourceKind.COMPANION.value,
            external_user_id="", token_ciphertext="", token_key_id="",
            status=SourceStatus.CONNECTED.value, last_ok_at=ts, meta={},
            created_at=ts, updated_at=ts,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "kind"],
            set_={"status": SourceStatus.CONNECTED.value, "last_ok_at": ts, "updated_at": ts},
        )
        await conn.execute(stmt)


async def _update_last_if_newer(res: Resources, user_id: UUID, event: ListenEvent,
                                observed_epoch: float) -> bool:
    key = last_key(user_id)
    current = await res.redis.hget(key, "event")
    if current:
        try:
            cur_played = datetime.fromisoformat(json.loads(current)["played_at"])
            if cur_played > event.played_at:
                return False
        except (ValueError, KeyError, TypeError):
            pass  # unreadable: overwrite
    await res.redis.hset(key, mapping=_hash_fields(event, observed_epoch))
    return True


async def ingest_submission(
    res: Resources, user_id: UUID, sub: Submission, received_at: datetime | None = None
) -> list[ListenEvent]:
    received_at = received_at or now()
    prepared = _prepare(sub, received_at)  # validates everything before any write
    resolver: IdentityResolver = res.resolver
    kind = EventKind.NOW_PLAYING if sub.listen_type == "playing_now" else EventKind.LISTEN
    via = COMPANION_ROUTE.via
    events: list[ListenEvent] = []
    first_play: dict[Platform, datetime] = {}

    for p in prepared:
        tm = p.listen.track_metadata
        ai = tm.additional_info
        track = RawTrack(
            artist=tm.artist_name, title=tm.track_name, album=tm.release_name,
            duration_ms=ai.effective_duration_ms,
        )
        resolved = await resolver.resolve(
            TrackInput(
                artist=tm.artist_name, title=tm.track_name, album=tm.release_name,
                duration_ms=track.duration_ms, isrc=ai.isrc,
                recording_mbid=ai.recording_uuid, release_mbid=ai.release_uuid,
            ),
            allow_remote=sub.listen_type != "import",
        )
        await _store_links(res.engine, resolved.recording_id, p.listen, p.platform)
        if kind is EventKind.NOW_PLAYING:
            # Enforced by type: only a live-capable route can produce a now-playing signal.
            NowPlaying.from_adapter(
                COMPANION_ROUTE, via=via, platform=p.platform, track=track, observed_at=received_at
            )
        events.append(
            ListenEvent(
                user_id=user_id, recording_id=resolved.recording_id, raw=track,
                artwork_url=resolved.artwork_url, platform=p.platform, via=via, kind=kind,
                played_at=p.played_at, observed_at=received_at,
                trainable=default_trainable(via, p.platform),
            )
        )
        prev = first_play.get(p.platform)
        first_play[p.platform] = p.played_at if prev is None else min(prev, p.played_at)

    obs_epoch = received_at.timestamp()
    if kind is EventKind.NOW_PLAYING:
        ev = events[0]
        pipe = res.redis.pipeline(transaction=True)
        pipe.hset(np_key(user_id), mapping=_hash_fields(ev, obs_epoch))
        pipe.expire(np_key(user_id), NP_TTL_SECONDS)
        await pipe.execute()
        await _update_last_if_newer(res, user_id, ev, obs_epoch)
    else:
        docs: list[dict[str, Any]] = [
            {
                "played_at": ev.played_at,
                "meta": {"user_id": str(user_id), "platform": ev.platform.value,
                         "via": ev.via.value},
                "recording_id": str(ev.recording_id) if ev.recording_id else None,
                "raw": ev.raw.model_dump(),
                "trainable": ev.trainable,
                "event_id": str(ev.event_id),
                "observed_at": ev.observed_at,
            }
            for ev in events
        ]
        await res.mongo[LISTENS].insert_many(docs, ordered=False)
        newest = max(events, key=lambda e: e.played_at)
        # Recent label time for a finished listen is when it was played, never in the future.
        await _update_last_if_newer(
            res, user_id, newest, min(newest.played_at.timestamp(), obs_epoch)
        )

    pipe = res.redis.pipeline(transaction=False)
    for ev in events:
        pipe.xadd(STREAM, {"data": ev.model_dump_json()}, maxlen=STREAM_MAXLEN, approximate=True)
    await pipe.execute()

    await _upsert_sources(res.engine, user_id, first_play, received_at)
    log.info("ingested %d %s event(s)", len(events), kind.value)
    return events
