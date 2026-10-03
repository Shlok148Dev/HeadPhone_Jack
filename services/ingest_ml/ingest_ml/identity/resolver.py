"""Identity resolver v1 (SRS 4.4).

Match order: ISRC → MusicBrainz recording MBID → local ``norm_key`` exact → MusicBrainz search
with rapidfuzz ``token_set_ratio ≥ 90`` (and duration within 5 s when both are known) → keep an
``unresolved`` Recording. The remote step is time-boxed; on timeout the listen stays unresolved
and the recording is queued on the Redis list ``resolve:pending`` for a later worker.
"""

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from rapidfuzz import fuzz
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from ..db import artists, now, recordings
from .musicbrainz import MBRecording, MusicBrainzClient, MusicBrainzUnavailable
from .normalize import NormalisedTrack, fold, normalise

log = logging.getLogger(__name__)

FUZZY_THRESHOLD = 90
DURATION_TOLERANCE_MS = 5_000
PENDING_KEY = "resolve:pending"  # list of jobs, FIFO
PENDING_IDS = "resolve:pending:ids"  # set of queued recording ids (dedupe)
PENDING_MAX = 50_000

RemoteGate = Callable[[], Awaitable[bool]]
_ISRC = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}\d{7}$")


def artwork_for(release_mbid: UUID | None) -> str | None:
    return f"https://coverartarchive.org/release/{release_mbid}/front-250" if release_mbid else None


def clean_isrc(value: str | None) -> str | None:
    if not value:
        return None
    v = value.replace("-", "").replace(" ", "").upper()
    return v if _ISRC.match(v) else None


@dataclass(frozen=True)
class TrackInput:
    artist: str
    title: str
    album: str | None = None
    duration_ms: int | None = None
    isrc: str | None = None
    recording_mbid: UUID | None = None
    release_mbid: UUID | None = None


@dataclass(frozen=True)
class Resolved:
    recording_id: UUID
    resolution: str  # isrc | mbid | fuzzy | unresolved
    artwork_url: str | None
    pending: bool = False  # queued for a later MusicBrainz lookup


def fuzzy_score(norm: NormalisedTrack, cand: MBRecording) -> float:
    """Worst of title and artist ``token_set_ratio`` on folded strings (0–100)."""
    cand_norm = normalise(cand.artist, cand.title)
    title = fuzz.token_set_ratio(norm.norm_title, cand_norm.norm_title)
    artist = fuzz.token_set_ratio(norm.norm_artist, fold(cand.artist))
    return float(min(title, artist))


def best_match(
    norm: NormalisedTrack, duration_ms: int | None, cands: list[MBRecording]
) -> MBRecording | None:
    best: tuple[float, int, MBRecording] | None = None
    for c in cands:
        too_far = bool(duration_ms and c.duration_ms) and (
            abs((duration_ms or 0) - (c.duration_ms or 0)) > DURATION_TOLERANCE_MS
        )
        if too_far:
            continue
        score = fuzzy_score(norm, c)
        if score < FUZZY_THRESHOLD:
            continue
        if best is None or (score, c.score) > (best[0], best[1]):
            best = (score, c.score, c)
    return best[2] if best else None


class IdentityResolver:
    def __init__(
        self,
        engine: AsyncEngine,
        redis: "Redis",
        musicbrainz: MusicBrainzClient | None,
        *,
        timeout: float = 1.5,
    ) -> None:
        self._engine = engine
        self._redis = redis
        self._mb = musicbrainz
        self._timeout = timeout

    # ---- lookups -------------------------------------------------------------------------
    @staticmethod
    async def _one(conn: AsyncConnection, where: Any) -> RowMapping | None:
        row = (await conn.execute(select(recordings).where(where).limit(1))).mappings().first()
        return row

    @staticmethod
    def _result(row: RowMapping, resolution: str | None = None) -> Resolved:
        art = row["artwork_url"] or artwork_for(row["release_mbid"])
        return Resolved(row["id"], resolution or row["resolution"], art or None)

    async def _enrich(self, conn: AsyncConnection, row: RowMapping, t: TrackInput) -> None:
        """Fill blanks on an existing row from what this push told us (never overwrite)."""
        values: dict[str, Any] = {}
        if t.release_mbid and not row["release_mbid"]:
            values["release_mbid"] = t.release_mbid
            if not row["artwork_url"]:
                values["artwork_url"] = artwork_for(t.release_mbid)
        if t.duration_ms and not row["duration_ms"]:
            values["duration_ms"] = t.duration_ms
        if t.album and not row["album"]:
            values["album"] = t.album[:500]
        if values:
            values["updated_at"] = now()
            stmt = update(recordings).where(recordings.c.id == row["id"]).values(values)
            await conn.execute(stmt)

    # ---- main entry ----------------------------------------------------------------------
    async def resolve(
        self,
        t: TrackInput,
        *,
        allow_remote: bool = True,
        remote_gate: RemoteGate | None = None,
    ) -> Resolved:
        """``remote_gate`` is awaited just before a MusicBrainz lookup (per-user budget);
        returning False defers the lookup to ``resolve:pending``."""
        norm = normalise(t.artist, t.title)
        isrc = clean_isrc(t.isrc)
        async with self._engine.begin() as conn:
            if isrc and (row := await self._one(conn, recordings.c.isrc == isrc)):
                await self._enrich(conn, row, t)
                return self._result(row)
            mbid = t.recording_mbid
            if mbid and (row := await self._one(conn, recordings.c.mbid == mbid)):
                if isrc and not row["isrc"]:
                    await self._set_ids(conn, row["id"], isrc=isrc)
                await self._enrich(conn, row, t)
                return self._result(row)
            local = await self._one(conn, recordings.c.norm_key == norm.norm_key[:600])
            if isrc or mbid:
                resolution = "isrc" if isrc else "mbid"
                if local and self._compatible(local, isrc, mbid):
                    await self._set_ids(
                        conn, local["id"], isrc=isrc, mbid=mbid, resolution=resolution
                    )
                    await self._enrich(conn, local, t)
                    return self._result(local, resolution)
                rid = await self._insert(conn, t, norm, isrc=isrc, mbid=mbid, resolution=resolution)
                return Resolved(rid, resolution, artwork_for(t.release_mbid))
            if local:
                await self._enrich(conn, local, t)
                return self._result(local)

        # Remote fuzzy match (outside the DB transaction).
        match: MBRecording | None = None
        pending = False
        if self._mb is not None and allow_remote and (remote_gate is None or await remote_gate()):
            try:
                cands = await asyncio.wait_for(
                    self._mb.search_recordings(norm.artist, norm.title), self._timeout
                )
                match = best_match(norm, t.duration_ms, cands)
            except (TimeoutError, MusicBrainzUnavailable) as exc:
                log.info("musicbrainz lookup deferred: %s", type(exc).__name__)
                pending = True
        elif self._mb is not None:
            pending = True

        async with self._engine.begin() as conn:
            if match is not None:
                return await self._store_match(conn, t, norm, match)
            rid = await self._insert(conn, t, norm, resolution="unresolved")
        if pending:
            await self._enqueue(rid, t)
        return Resolved(rid, "unresolved", artwork_for(t.release_mbid), pending=pending)

    @staticmethod
    def _compatible(row: RowMapping, isrc: str | None, mbid: UUID | None) -> bool:
        isrc_ok = not isrc or row["isrc"] in (None, isrc)
        return isrc_ok and (not mbid or row["mbid"] in (None, mbid))

    async def _set_ids(
        self,
        conn: AsyncConnection,
        rid: UUID,
        *,
        isrc: str | None = None,
        mbid: UUID | None = None,
        resolution: str | None = None,
    ) -> None:
        values: dict[str, Any] = {"updated_at": now()}
        if isrc:
            values["isrc"] = isrc
        if mbid:
            values["mbid"] = mbid
        if resolution:
            values["resolution"] = resolution
        try:
            async with conn.begin_nested():
                await conn.execute(update(recordings).where(recordings.c.id == rid).values(values))
        except IntegrityError:
            log.info("identifier already attached to another recording; left unchanged")

    async def _insert(
        self,
        conn: AsyncConnection,
        t: TrackInput,
        norm: NormalisedTrack,
        *,
        resolution: str,
        isrc: str | None = None,
        mbid: UUID | None = None,
        title: str | None = None,
        artist_name: str | None = None,
        album: str | None = None,
        release_mbid: UUID | None = None,
        duration_ms: int | None = None,
        artist_id: UUID | None = None,
    ) -> UUID:
        rid = uuid4()
        rel = release_mbid or t.release_mbid
        ts = now()
        values = {
            "id": rid,
            "isrc": isrc,
            "mbid": mbid,
            "title": (title or norm.title)[:500],
            "artist_name": (artist_name or t.artist.strip() or norm.artist)[:500],
            "album": (album or t.album or "")[:500],
            "release_mbid": rel,
            "duration_ms": duration_ms or t.duration_ms,
            "artwork_url": artwork_for(rel) or "",
            "artist_id": artist_id,
            "norm_key": norm.norm_key[:600],
            "resolution": resolution,
            "created_at": ts,
            "updated_at": ts,
        }
        try:
            async with conn.begin_nested():
                await conn.execute(recordings.insert().values(values))
        except IntegrityError:
            # Lost a race on the ISRC/MBID unique index: use the winner.
            where = recordings.c.isrc == isrc if isrc else recordings.c.mbid == mbid
            row = await self._one(conn, where)
            if row is None:
                raise
            return UUID(str(row["id"]))
        return rid

    async def _upsert_artist(
        self, conn: AsyncConnection, name: str, mbid: UUID | None
    ) -> UUID | None:
        if mbid is None:
            return None
        row = (await conn.execute(select(artists.c.id).where(artists.c.mbid == mbid))).first()
        if row:
            return UUID(str(row[0]))
        aid = uuid4()
        ts = now()
        try:
            async with conn.begin_nested():
                await conn.execute(
                    artists.insert().values(
                        id=aid, mbid=mbid, name=name[:300], created_at=ts, updated_at=ts
                    )
                )
        except IntegrityError:
            row = (await conn.execute(select(artists.c.id).where(artists.c.mbid == mbid))).first()
            return UUID(str(row[0])) if row else None
        return aid

    async def _store_match(
        self, conn: AsyncConnection, t: TrackInput, norm: NormalisedTrack, m: MBRecording
    ) -> Resolved:
        existing = await self._one(conn, recordings.c.mbid == m.mbid)
        if existing:  # permanent cache: this MBID is already a Recording
            return self._result(existing)
        isrc = clean_isrc(m.isrc)
        if isrc and await self._one(conn, recordings.c.isrc == isrc):
            isrc = None
        artist_id = await self._upsert_artist(conn, m.artist, m.artist_mbid)
        rid = await self._insert(
            conn,
            t,
            norm,
            resolution="fuzzy",
            mbid=m.mbid,
            isrc=isrc,
            title=m.title,
            artist_name=m.artist,
            album=m.release_title,
            release_mbid=m.release_mbid or t.release_mbid,
            duration_ms=m.duration_ms,
            artist_id=artist_id,
        )
        return Resolved(rid, "fuzzy", artwork_for(m.release_mbid or t.release_mbid))

    async def _enqueue(self, rid: UUID, t: TrackInput) -> None:
        """Queue once per recording id, bounded at PENDING_MAX jobs."""
        if not await self._redis.sadd(PENDING_IDS, str(rid)):
            return  # already queued
        if await self._redis.llen(PENDING_KEY) >= PENDING_MAX:
            await self._redis.srem(PENDING_IDS, str(rid))
            log.warning("resolve:pending is full; recording left unresolved")
            return
        job = {
            "recording_id": str(rid),
            "artist": t.artist,
            "title": t.title,
            "duration_ms": t.duration_ms,
        }
        await self._redis.rpush(PENDING_KEY, json.dumps(job))

    async def drain_pending(self, limit: int = 20) -> dict[str, int]:
        """Consume up to ``limit`` queued lookups (called by a periodic job).

        Stops early and re-queues the job when MusicBrainz is rate-limited or down.
        """
        counts = {"processed": 0, "resolved": 0, "requeued": 0, "skipped": 0}
        if self._mb is None:
            return counts
        for _ in range(max(0, limit)):
            popped = await self._redis.lpop(PENDING_KEY)
            if popped is None or isinstance(popped, list):
                break
            raw: str | bytes = popped
            counts["processed"] += 1
            try:
                job = json.loads(raw)
                rid = UUID(str(job["recording_id"]))
            except (ValueError, KeyError, TypeError):
                counts["skipped"] += 1
                continue
            async with self._engine.connect() as conn:
                row = await self._one(conn, recordings.c.id == rid)
            if row is None or row["resolution"] != "unresolved":
                await self._redis.srem(PENDING_IDS, str(rid))
                counts["skipped"] += 1
                continue
            try:
                cands = await self._mb.search_recordings(row["artist_name"], row["title"])
            except MusicBrainzUnavailable:
                await self._redis.lpush(PENDING_KEY, raw)
                counts["requeued"] += 1
                break
            await self._redis.srem(PENDING_IDS, str(rid))
            norm = normalise(row["artist_name"], row["title"])
            match = best_match(norm, row["duration_ms"], cands)
            if match is not None and await self._apply_match(rid, match):
                counts["resolved"] += 1
        return counts

    async def _apply_match(self, rid: UUID, m: MBRecording) -> bool:
        """Upgrade an unresolved row in place. Skips if the MBID already has its own row."""
        async with self._engine.begin() as conn:
            if await self._one(conn, recordings.c.mbid == m.mbid):
                return False
            isrc = clean_isrc(m.isrc)
            if isrc and await self._one(conn, recordings.c.isrc == isrc):
                isrc = None
            artist_id = await self._upsert_artist(conn, m.artist, m.artist_mbid)
            values: dict[str, Any] = {
                "mbid": m.mbid,
                "resolution": "fuzzy",
                "artist_id": artist_id,
                "updated_at": now(),
            }
            if isrc:
                values["isrc"] = isrc
            if m.release_mbid:
                values["release_mbid"] = m.release_mbid
                values["artwork_url"] = artwork_for(m.release_mbid)
            if m.release_title:
                values["album"] = m.release_title[:500]
            if m.duration_ms:
                values["duration_ms"] = m.duration_ms
            try:
                async with conn.begin_nested():
                    await conn.execute(
                        update(recordings).where(recordings.c.id == rid).values(values)
                    )
            except IntegrityError:
                return False
        return True
