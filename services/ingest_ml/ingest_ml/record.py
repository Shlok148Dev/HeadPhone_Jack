"""Write plays from any route into Jingle's stores (CONTRACTS.md §5, §6).

Push (Companion), polled adapters (ListenBrainz, Last.fm, direct Spotify) and exports (YouTube
Takeout) all end here, so identity resolution, de-duplication, lineage flags and the no-false-Live
rule (BR-01) behave identically whatever the route. ``observed_at`` is always Jingle's receive or
poll time; a source's clock only sets ``played_at``.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4, uuid5

from jingle_common.enums import LIVE_MAX_AGE_SECONDS, EventKind, Platform, SourceKind, SourceStatus
from jingle_common.events import (
    ListenEvent,
    RawTrack,
    default_analytics_allowed,
    default_trainable,
)
from redis.typing import EncodableT, FieldT
from sqlalchemy import case, func, update
from sqlalchemy.ext.asyncio import AsyncEngine

from .adapters.base import HasCapabilities, NowPlaying
from .db import dialect_insert, linked_sources, now, platform_connections, recording_links
from .identity.resolver import IdentityResolver, TrackInput
from .push.platform import external_id_from_url
from .resources import Resources
from .stores import LISTENS

log = logging.getLogger(__name__)

STREAM = "events:listen"
STREAM_RETENTION = timedelta(days=7)  # entries carry user ids; trimmed by age (DPDP)
DEDUPE_TTL_SECONDS = 86_400  # repeats within 24 h are ignored (older re-imports are not)
_EVENT_NS = UUID("6f1c2b8e-7d4a-4c1e-9b0a-4a7d1e2f3c5d")
NP_TTL_SECONDS = LIVE_MAX_AGE_SECONDS  # 90 s; refreshed by every now-playing signal (BR-01)


@dataclass
class Play:
    """One play, normalised from any route."""

    track: RawTrack
    played_at: datetime
    platform: Platform
    isrc: str | None = None
    recording_mbid: UUID | None = None
    release_mbid: UUID | None = None
    # Already validated, canonical platform links (see push.platform.safe_platform_url).
    links: dict[Platform, str] = field(default_factory=dict)
    # Artwork supplied by the source for display with this event only (never the shared catalog).
    artwork_url: str | None = None
    played_at_estimated: bool = False


def np_key(user_id: UUID) -> str:
    return f"np:{user_id}"


def last_key(user_id: UUID) -> str:
    return f"last:{user_id}"


def _hash_fields(event: ListenEvent, observed_epoch: float) -> dict[FieldT, EncodableT]:
    return {
        "event": event.model_dump_json(),
        "observed_at": f"{observed_epoch:.3f}",
        "via": event.via.value,
        "platform": event.platform.value,
    }


async def _store_links(engine: AsyncEngine, recording_id: UUID, links: dict[Platform, str]) -> None:
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
            # Never overwrite an existing shared link (SEC H1): the first verified link wins.
            await conn.execute(
                stmt.on_conflict_do_nothing(index_elements=["recording_id", "platform"])
            )


async def _upsert_sources(
    engine: AsyncEngine,
    user_id: UUID,
    first_play: dict[Platform, datetime],
    ts: datetime,
    source_kind: SourceKind,
) -> None:
    """First accepted play flips a platform connection to CONNECTED; the route stays healthy."""
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
        if source_kind is SourceKind.COMPANION:
            stmt = dialect_insert(conn, ls).values(
                id=uuid4(), user_id=user_id, kind=SourceKind.COMPANION.value,
                external_user_id="", token_ciphertext="", token_key_id="",
                status=SourceStatus.CONNECTED.value, last_ok_at=ts, meta={},
                created_at=ts, updated_at=ts,
            )
            await conn.execute(stmt.on_conflict_do_update(
                index_elements=["user_id", "kind"],
                set_={"status": SourceStatus.CONNECTED.value, "last_ok_at": ts, "updated_at": ts},
            ))
        else:
            await conn.execute(
                update(ls)
                .where(ls.c.user_id == user_id, ls.c.kind == source_kind.value)
                .values(status=SourceStatus.CONNECTED.value, last_ok_at=ts, updated_at=ts)
            )


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


def _dedupe_key(user_id: UUID, played_at: datetime, track: RawTrack) -> str:
    norm = f"{track.artist.casefold().strip()}|{track.title.casefold().strip()}"
    digest = hashlib.sha1(norm.encode(), usedforsecurity=False).hexdigest()
    return f"dedupe:{user_id}:{int(played_at.timestamp())}:{digest}"


def _event_id(user_id: UUID, kind: EventKind, played_at: datetime, track: RawTrack) -> UUID:
    name = f"{user_id}|{kind.value}|{played_at.isoformat()}|{track.artist}|{track.title}"
    return uuid5(_EVENT_NS, name)


def _mongo_doc(ev: ListenEvent) -> dict[str, Any]:
    doc = ev.model_dump(mode="python", exclude={"user_id", "platform", "via"})
    doc["meta"] = {"user_id": str(ev.user_id), "platform": ev.platform.value, "via": ev.via.value}
    doc["event_id"] = str(ev.event_id)
    doc["recording_id"] = str(ev.recording_id) if ev.recording_id else None
    doc["kind"] = ev.kind.value
    return doc


async def _claim_new(res: Resources, user_id: UUID, events: list[ListenEvent]) -> list[ListenEvent]:
    """Drop listens already stored in the last 24 h (resends, retries, overlapping polls)."""
    pipe = res.redis.pipeline(transaction=False)
    for ev in events:
        pipe.set(_dedupe_key(user_id, ev.played_at, ev.raw), "1", nx=True, ex=DEDUPE_TTL_SECONDS)
    claimed = await pipe.execute()
    return [ev for ev, ok in zip(events, claimed, strict=True) if ok]


async def _release(res: Resources, user_id: UUID, events: list[ListenEvent]) -> None:
    if events:
        await res.redis.delete(*[_dedupe_key(user_id, ev.played_at, ev.raw) for ev in events])


async def record_plays(
    res: Resources,
    user_id: UUID,
    plays: list[Play],
    *,
    kind: EventKind,
    route: HasCapabilities,
    via: Any,
    received_at: datetime | None = None,
    allow_remote: bool = True,
    catalog_writes: bool = True,
) -> list[ListenEvent]:
    """Resolve, de-duplicate and store ``plays``; return the events actually written.

    ``catalog_writes=False`` keeps the source's links and artwork out of the shared catalog
    (direct Spotify API data is display-only, BR-03 / ADR-0007).
    """
    if not plays:
        return []
    received_at = received_at or now()
    resolver: IdentityResolver = res.resolver
    events: list[ListenEvent] = []
    first_play: dict[Platform, datetime] = {}

    if allow_remote:  # per-user share of the global 1 req/s MusicBrainz budget (SEC M3)
        allow_remote = (await res.mb_user_bucket.take(f"rl:mb:user:{user_id}")).allowed

    for p in plays:
        resolved = await resolver.resolve(
            TrackInput(
                artist=p.track.artist, title=p.track.title, album=p.track.album,
                duration_ms=p.track.duration_ms, isrc=p.isrc,
                recording_mbid=p.recording_mbid, release_mbid=p.release_mbid,
            ),
            allow_remote=allow_remote,
        )
        if catalog_writes:
            await _store_links(res.engine, resolved.recording_id, p.links)
        if kind is EventKind.NOW_PLAYING:
            # Enforced by type: only a live-capable route can produce a now-playing signal.
            NowPlaying.from_adapter(
                route, via=via, platform=p.platform, track=p.track, observed_at=received_at
            )
        events.append(
            ListenEvent(
                event_id=_event_id(user_id, kind, p.played_at, p.track),
                user_id=user_id, recording_id=resolved.recording_id, raw=p.track,
                artwork_url=p.artwork_url or resolved.artwork_url,
                platform=p.platform, via=via, kind=kind,
                played_at=p.played_at, observed_at=received_at,
                trainable=default_trainable(via, p.platform),
                analytics_allowed=default_analytics_allowed(via, p.platform),
                played_at_estimated=p.played_at_estimated,
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
        events = await _claim_new(res, user_id, events)
        if not events:
            log.info("ignored duplicate listen(s)")
            return []
        try:
            await res.mongo[LISTENS].insert_many([_mongo_doc(ev) for ev in events], ordered=False)
        except Exception:
            await _release(res, user_id, events)  # let the retry through
            raise
        newest = max(events, key=lambda e: e.played_at)
        # Recent label time for a finished listen is when it was played, never in the future.
        await _update_last_if_newer(
            res, user_id, newest, min(newest.played_at.timestamp(), obs_epoch)
        )

    min_id = f"{int((received_at - STREAM_RETENTION).timestamp() * 1000)}-0"
    pipe = res.redis.pipeline(transaction=False)
    for ev in events:
        pipe.xadd(STREAM, {"data": ev.model_dump_json()}, minid=min_id, approximate=True)
    await pipe.execute()

    await _upsert_sources(res.engine, user_id, first_play, received_at, route.kind)
    log.info("recorded %d %s event(s) via %s", len(events), kind.value, route.kind.value)
    return events
