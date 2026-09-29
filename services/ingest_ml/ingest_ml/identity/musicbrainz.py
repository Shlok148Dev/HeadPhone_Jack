"""MusicBrainz recording search (https://musicbrainz.org/doc/MusicBrainz_API/Search).

MusicBrainz allows 1 request/second per client and requires a meaningful User-Agent. A global
Redis token bucket (``rl:musicbrainz``, capacity 1, 1/s) enforces the limit across replicas.
Results are cached permanently in ``recordings`` by the resolver, not here.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from redis.asyncio import Redis

from ..ratelimit import TokenBucket

log = logging.getLogger(__name__)

BUCKET_KEY = "rl:musicbrainz"


class MusicBrainzUnavailable(Exception):
    """Rate limited, timed out or returned an error; caller keeps the listen unresolved."""


@dataclass(frozen=True)
class MBRecording:
    mbid: UUID
    title: str
    artist: str
    artist_mbid: UUID | None
    duration_ms: int | None
    isrc: str | None
    release_mbid: UUID | None
    release_title: str | None
    score: int


def _lucene(text: str) -> str:
    escaped = "".join("\\" + c if c in '+-&|!(){}[]^"~*?:\\/' else c for c in text)
    return f'"{escaped}"'


def _uuid(value: Any) -> UUID | None:
    try:
        return UUID(str(value)) if value else None
    except ValueError:
        return None


def parse_recording(item: dict[str, Any]) -> MBRecording | None:
    mbid = _uuid(item.get("id"))
    if mbid is None or not item.get("title"):
        return None
    credits = item.get("artist-credit") or []
    artist = "".join(
        str(c.get("name", "")) + str(c.get("joinphrase", ""))
        for c in credits
        if isinstance(c, dict)
    )
    first = credits[0] if credits and isinstance(credits[0], dict) else {}
    artist_mbid = _uuid((first.get("artist") or {}).get("id"))
    releases = item.get("releases") or []
    release = releases[0] if releases and isinstance(releases[0], dict) else {}
    isrcs = item.get("isrcs") or []
    length = item.get("length")
    return MBRecording(
        mbid=mbid,
        title=str(item["title"]),
        artist=artist.strip(),
        artist_mbid=artist_mbid,
        duration_ms=int(length) if isinstance(length, int | float) else None,
        isrc=str(isrcs[0]) if isrcs else None,
        release_mbid=_uuid(release.get("id")),
        release_title=release.get("title"),
        score=int(item.get("score", 0) or 0),
    )


class MusicBrainzClient:
    def __init__(
        self,
        http: httpx.AsyncClient,
        redis: "Redis",
        *,
        user_agent: str,
        base_url: str = "https://musicbrainz.org/ws/2",
    ) -> None:
        self._http = http
        self._bucket = TokenBucket(redis, capacity=1, per_seconds=1.0)
        self._ua = user_agent
        self._base = base_url.rstrip("/")

    async def _acquire(self, max_wait: float = 1.0) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + max_wait
        while True:
            res = await self._bucket.take(BUCKET_KEY)
            if res.allowed:
                return
            if loop.time() + res.retry_after > deadline:
                raise MusicBrainzUnavailable("musicbrainz rate budget exhausted")
            await asyncio.sleep(res.retry_after)

    async def search_recordings(self, artist: str, title: str, limit: int = 5) -> list[MBRecording]:
        await self._acquire()
        query = f"recording:{_lucene(title)} AND artist:{_lucene(artist)}"
        try:
            resp = await self._http.get(
                f"{self._base}/recording",
                params={"query": query, "fmt": "json", "limit": str(limit)},
                headers={"User-Agent": self._ua, "Accept": "application/json"},
                timeout=httpx.Timeout(3.0),
            )
        except httpx.HTTPError as exc:
            raise MusicBrainzUnavailable(type(exc).__name__) from exc
        if resp.status_code != 200:
            log.warning("musicbrainz search returned %s", resp.status_code)
            raise MusicBrainzUnavailable(f"status {resp.status_code}")
        body = resp.json()
        results = [parse_recording(r) for r in body.get("recordings", []) if isinstance(r, dict)]
        return [r for r in results if r is not None]
