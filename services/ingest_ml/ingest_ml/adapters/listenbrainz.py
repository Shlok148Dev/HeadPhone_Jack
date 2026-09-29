"""ListenBrainz adapter (docs/research/listenbrainz.md): user token, playing-now, listens, stats.

ListenBrainz data is openly licensed, so it may train models (BR-04). ``platform`` comes from the
listen's ``music_service``/``origin_url`` when present, else the platform the user connected.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from jingle_common.crypto import TokenCipher
from jingle_common.enums import Platform, SourceKind, SourceStatus, Via
from jingle_common.events import RawTrack

from ..push.platform import infer_platform, safe_platform_url
from ..ratelimit import TokenBucket
from ..record import Play
from .base import (
    Capabilities,
    LinkCredential,
    LinkedSource,
    NotSupported,
    NowPlaying,
    PlaylistSpec,
    RawListen,
    Window,
)
from .common import AdapterError, ReauthRequired, request_json, seal, unseal

_RANGE = {
    Window.WEEK: "week",
    Window.MONTH: "month",
    Window.YEAR: "year",
    Window.ALL_TIME: "all_time",
}


def _uuid(v: Any) -> UUID | None:
    try:
        return UUID(str(v)) if v else None
    except ValueError:
        return None


def play_from_listen(item: dict[str, Any], fallback: Platform, played_at: datetime) -> Play | None:
    tm = item.get("track_metadata") or {}
    artist, title = tm.get("artist_name"), tm.get("track_name")
    if not artist or not title:
        return None
    ai = tm.get("additional_info") or {}
    mapping = tm.get("mbid_mapping") or {}
    platform = infer_platform(
        ai.get("music_service"), ai.get("origin_url"), ai.get("music_service_name")
    )
    if platform is Platform.UNKNOWN:
        platform = fallback
    dur = ai.get("duration_ms") or (
        int(ai["duration"]) * 1000 if str(ai.get("duration", "")).isdigit() else None
    )
    links: dict[Platform, str] = {}
    if url := safe_platform_url(ai.get("origin_url"), platform):
        links[platform] = url
    return Play(
        track=RawTrack(
            artist=str(artist)[:500],
            title=str(title)[:500],
            album=(tm.get("release_name") or None),
            duration_ms=dur,
        ),
        played_at=played_at,
        platform=platform,
        isrc=ai.get("isrc"),
        recording_mbid=_uuid(ai.get("recording_mbid") or mapping.get("recording_mbid")),
        release_mbid=_uuid(ai.get("release_mbid") or mapping.get("release_mbid")),
        links=links,
    )


class ListenBrainzAdapter:
    kind = SourceKind.LISTENBRAINZ
    via = Via.LISTENBRAINZ
    caps = Capabilities(live=True, recent=True, top=True, playlist_write=False, trainable=True)

    def __init__(
        self,
        http: httpx.AsyncClient,
        cipher: TokenCipher,
        bucket: TokenBucket,
        base_url: str = "https://api.listenbrainz.org",
    ) -> None:
        self.http, self.cipher, self.bucket, self.base = http, cipher, bucket, base_url.rstrip("/")

    async def _get(self, path: str, token: str | None = None, **params: Any) -> Any:
        headers = {"Authorization": f"Token {token}"} if token else {}
        _, data = await request_json(
            self.http,
            "GET",
            f"{self.base}{path}",
            bucket=self.bucket,
            bucket_key="rl:src:listenbrainz",
            headers=headers,
            params=params or None,
        )
        return data

    def _token(self, src: LinkedSource) -> str:
        return str(unseal(self.cipher, src.token_ciphertext, src.user_id)["token"])

    async def link(self, user_id: UUID, credential: LinkCredential) -> LinkedSource:
        if not credential.token:
            raise ReauthRequired("missing_token")
        data = await self._get("/1/validate-token", credential.token)
        if not isinstance(data, dict) or not data.get("valid"):
            raise ReauthRequired("invalid_token")
        return LinkedSource(
            user_id=user_id,
            kind=self.kind,
            external_user_id=str(data.get("user_name", "")),
            token_ciphertext=seal(self.cipher, {"token": credential.token}, user_id),
            token_key_id=self.cipher.kek_id,
            status=SourceStatus.PENDING_FIRST_PLAY,
        )

    async def refresh(self, src: LinkedSource) -> LinkedSource:
        return src

    async def poll_now(self, src: LinkedSource, now: datetime) -> Play | None:
        data = await self._get(f"/1/user/{src.external_user_id}/playing-now", self._token(src))
        listens = ((data or {}).get("payload") or {}).get("listens") or []
        if not listens:
            return None
        return play_from_listen(listens[0], Platform(src.meta.get("platform", "UNKNOWN")), now)

    async def recent_plays(self, src: LinkedSource, since: datetime) -> list[Play]:
        data = await self._get(
            f"/1/user/{src.external_user_id}/listens",
            self._token(src),
            min_ts=int(since.timestamp()),
            count=100,
        )
        out: list[Play] = []
        fallback = Platform(src.meta.get("platform", "UNKNOWN"))
        for item in ((data or {}).get("payload") or {}).get("listens") or []:
            ts = item.get("listened_at")
            if not isinstance(ts, int):
                continue
            if play := play_from_listen(item, fallback, datetime.fromtimestamp(ts, UTC)):
                out.append(play)
        return out

    # ---- SourceAdapter protocol (Technical Bible 2.1) -------------------------------------
    async def now_playing(self, src: LinkedSource) -> NowPlaying | None:
        play = await self.poll_now(src, datetime.now(UTC))
        if play is None:
            return None
        return NowPlaying.from_adapter(self, via=self.via, platform=play.platform, track=play.track)

    async def recent(self, src: LinkedSource, since: datetime) -> list[RawListen]:
        return [
            RawListen(
                track=p.track,
                played_at=p.played_at,
                platform=p.platform,
                isrc=p.isrc,
                recording_mbid=p.recording_mbid,
                release_mbid=p.release_mbid,
            )
            for p in await self.recent_plays(src, since)
        ]

    async def top(self, src: LinkedSource, window: Window) -> list[RawTrack]:
        data = await self._get(
            f"/1/stats/user/{src.external_user_id}/recordings",
            self._token(src),
            range=_RANGE[window],
            count=50,
        )
        recs = ((data or {}).get("payload") or {}).get("recordings") or []
        return [
            RawTrack(artist=r["artist_name"], title=r["track_name"], album=r.get("release_name"))
            for r in recs
            if r.get("artist_name") and r.get("track_name")
        ]

    async def write_playlist(self, src: LinkedSource, pl: PlaylistSpec) -> str:
        raise NotSupported("Jingle does not write ListenBrainz playlists")


__all__ = ["AdapterError", "ListenBrainzAdapter", "play_from_listen"]
