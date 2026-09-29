"""Last.fm adapter (docs/research/lastfm.md).

Carries Spotify listeners on every device through Spotify's built-in Last.fm link (ADR-0003).
Terms: non-commercial, "powered by AudioScrobbler" credit (Settings), never used for training
(``trainable=False``, BR-04). Linking needs the user's explicit consent (ADR-0016).
"""

import hashlib
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from jingle_common.crypto import TokenCipher
from jingle_common.enums import Platform, SourceKind, SourceStatus, Via
from jingle_common.events import RawTrack

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
from .common import AdapterError, RateLimited, ReauthRequired, request_json, seal

API = "https://ws.audioscrobbler.com/2.0/"
AUTH_URL = "https://www.last.fm/api/auth/"
_PERIOD = {
    Window.WEEK: "7day",
    Window.MONTH: "1month",
    Window.YEAR: "12month",
    Window.ALL_TIME: "overall",
}
# Last.fm error codes: 29 rate limit; 17 private profile; 6 no such user; 4/9/14/15 auth problems.
_REAUTH_CODES = {
    4: "invalid_token",
    6: "user_not_found",
    9: "invalid_session",
    14: "token_unauthorised",
    15: "token_expired",
    17: "private_profile",
}


def api_sig(params: dict[str, str], secret: str) -> str:
    """md5 of sorted key+value pairs (excluding format/callback) + shared secret."""
    base = "".join(f"{k}{params[k]}" for k in sorted(params) if k not in ("format", "callback"))
    return hashlib.md5((base + secret).encode(), usedforsecurity=False).hexdigest()


def _text(v: Any) -> str:
    if isinstance(v, dict):
        return str(v.get("#text") or v.get("name") or "")
    return str(v or "")


def _uuid(v: Any) -> UUID | None:
    try:
        return UUID(str(v)) if v else None
    except ValueError:
        return None


def play_from_track(t: dict[str, Any], platform: Platform, played_at: datetime) -> Play | None:
    artist, title = _text(t.get("artist")), _text(t.get("name"))
    if not artist or not title:
        return None
    album = _text(t.get("album")) or None
    return Play(
        track=RawTrack(artist=artist[:500], title=title[:500], album=album),
        played_at=played_at,
        platform=platform,
        recording_mbid=_uuid(t.get("mbid")),
        release_mbid=_uuid(
            t.get("album", {}).get("mbid") if isinstance(t.get("album"), dict) else None
        ),
    )


class LastfmAdapter:
    kind = SourceKind.LASTFM
    via = Via.LASTFM
    caps = Capabilities(live=True, recent=True, top=True, playlist_write=False, trainable=False)

    def __init__(
        self,
        http: httpx.AsyncClient,
        cipher: TokenCipher,
        bucket: TokenBucket,
        api_key: str,
        shared_secret: str,
    ) -> None:
        self.http, self.cipher, self.bucket = http, cipher, bucket
        self.api_key, self.secret = api_key, shared_secret

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.secret)

    def auth_url(self, callback_url: str) -> str:
        return f"{AUTH_URL}?{urlencode({'api_key': self.api_key, 'cb': callback_url})}"

    async def _call(
        self, method: str, params: dict[str, str] | None = None, *, signed: bool = False
    ) -> dict[str, Any]:
        if not self.configured:
            raise AdapterError("lastfm not configured")
        q = {"method": method, "api_key": self.api_key, **(params or {})}
        if signed:
            q["api_sig"] = api_sig(q, self.secret)
        q["format"] = "json"
        _, data = await request_json(
            self.http, "GET", API, bucket=self.bucket, bucket_key="rl:src:lastfm", params=q
        )
        if not isinstance(data, dict):
            raise AdapterError("unexpected Last.fm response")
        if "error" in data:
            code = int(data.get("error", 0))
            if code == 29:
                raise RateLimited(60)
            if code in _REAUTH_CODES:
                raise ReauthRequired(_REAUTH_CODES[code])
            raise AdapterError(f"lastfm error {code}")
        return data

    async def link(self, user_id: UUID, credential: LinkCredential) -> LinkedSource:
        if credential.token:  # web auth: exchange the callback token for a session
            data = await self._call("auth.getSession", {"token": credential.token}, signed=True)
            session = data.get("session") or {}
            name, key = str(session.get("name", "")), str(session.get("key", ""))
            if not name:
                raise ReauthRequired("invalid_token")
            cipher_text = seal(self.cipher, {"session_key": key}, user_id)
        elif credential.username:  # public profile by username (still needs consent)
            data = await self._call("user.getInfo", {"user": credential.username})
            name, cipher_text = str((data.get("user") or {}).get("name", "")), ""
            if not name:
                raise ReauthRequired("user_not_found")
        else:
            raise ReauthRequired("missing_credential")
        return LinkedSource(
            user_id=user_id,
            kind=self.kind,
            external_user_id=name,
            token_ciphertext=cipher_text,
            token_key_id=self.cipher.kek_id if cipher_text else "",
            status=SourceStatus.PENDING_FIRST_PLAY,
        )

    async def refresh(self, src: LinkedSource) -> LinkedSource:
        return src

    async def _recent(self, src: LinkedSource, params: dict[str, str]) -> list[dict[str, Any]]:
        data = await self._call("user.getRecentTracks", {"user": src.external_user_id, **params})
        tracks = (data.get("recenttracks") or {}).get("track") or []
        return tracks if isinstance(tracks, list) else [tracks]

    async def poll_now(self, src: LinkedSource, now: datetime) -> Play | None:
        platform = Platform(src.meta.get("platform", "UNKNOWN"))
        for t in await self._recent(src, {"limit": "1"}):
            if (t.get("@attr") or {}).get("nowplaying") == "true":
                return play_from_track(t, platform, now)
        return None

    async def recent_plays(self, src: LinkedSource, since: datetime) -> list[Play]:
        platform = Platform(src.meta.get("platform", "UNKNOWN"))
        out: list[Play] = []
        for t in await self._recent(src, {"limit": "200", "from": str(int(since.timestamp()) + 1)}):
            if (t.get("@attr") or {}).get("nowplaying") == "true":
                continue
            uts = str((t.get("date") or {}).get("uts") or "")
            if not uts.isdigit():
                continue
            if play := play_from_track(t, platform, datetime.fromtimestamp(int(uts), UTC)):
                out.append(play)
        return out

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
                recording_mbid=p.recording_mbid,
                release_mbid=p.release_mbid,
            )
            for p in await self.recent_plays(src, since)
        ]

    async def top(self, src: LinkedSource, window: Window) -> list[RawTrack]:
        data = await self._call(
            "user.getTopTracks",
            {"user": src.external_user_id, "period": _PERIOD[window], "limit": "50"},
        )
        tracks = (data.get("toptracks") or {}).get("track") or []
        return [
            RawTrack(artist=_text(t.get("artist")), title=_text(t.get("name")))
            for t in tracks
            if _text(t.get("artist")) and _text(t.get("name"))
        ]

    async def write_playlist(self, src: LinkedSource, pl: PlaylistSpec) -> str:
        raise NotSupported("Last.fm has no playlist write API")
