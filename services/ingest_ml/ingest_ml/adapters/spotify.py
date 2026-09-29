"""Direct Spotify adapter for up to 5 allowlisted testers (docs/research/spotify.md, ADR-0013).

OAuth 2.0 Authorization Code with PKCE. Development Mode returns no ISRC and no email, so identity
resolution falls back to MusicBrainz/fuzzy matching. Spotify API data is display-only: events carry
``trainable=False`` and ``analytics_allowed=False`` (via DIRECT + SPOTIFY), nothing is
written to the shared catalog, and everything is deleted when the user unlinks (BR-03, ADR-0007).
"""

import base64
import hashlib
import secrets
import time
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
from .common import AdapterError, ReauthRequired, request_json, seal, unseal

AUTHORIZE = "https://accounts.spotify.com/authorize"
TOKEN = "https://accounts.spotify.com/api/token"  # noqa: S105 - URL, not a secret
API = "https://api.spotify.com/v1"
SCOPES = "user-read-currently-playing user-read-recently-played user-top-read"
MAX_DIRECT_USERS = 5  # Development Mode cap (Feb 2026)
_RANGE = {
    Window.WEEK: "short_term",
    Window.MONTH: "short_term",
    Window.YEAR: "medium_term",
    Window.ALL_TIME: "long_term",
}


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    return verifier, challenge


def _artwork(item: dict[str, Any]) -> str | None:
    images = (item.get("album") or {}).get("images") or []
    url = images[0].get("url") if images else None
    return url if isinstance(url, str) and url.startswith("https://i.scdn.co/") else None


def play_from_item(item: dict[str, Any], played_at: datetime) -> Play | None:
    if not item or item.get("type", "track") != "track":
        return None  # podcasts/episodes are out of scope
    artists = ", ".join(a.get("name", "") for a in item.get("artists") or [] if a.get("name"))
    title = item.get("name")
    if not artists or not title:
        return None
    return Play(
        track=RawTrack(
            artist=artists[:500],
            title=str(title)[:500],
            album=(item.get("album") or {}).get("name"),
            duration_ms=item.get("duration_ms"),
        ),
        played_at=played_at,
        platform=Platform.SPOTIFY,
        artwork_url=_artwork(item),  # shown with Spotify attribution on this event only
    )


class SpotifyAdapter:
    kind = SourceKind.SPOTIFY
    via = Via.DIRECT
    caps = Capabilities(live=True, recent=True, top=True, playlist_write=True, trainable=False)

    def __init__(
        self,
        http: httpx.AsyncClient,
        cipher: TokenCipher,
        bucket: TokenBucket,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> None:
        self.http, self.cipher, self.bucket = http, cipher, bucket
        self.client_id, self.client_secret, self.redirect_uri = (
            client_id,
            client_secret,
            redirect_uri,
        )

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.redirect_uri)

    def authorize_url(self, state: str, code_challenge: str) -> str:
        return f"{AUTHORIZE}?" + urlencode(
            {
                "client_id": self.client_id,
                "response_type": "code",
                "redirect_uri": self.redirect_uri,
                "code_challenge_method": "S256",
                "code_challenge": code_challenge,
                "state": state,
                "scope": SCOPES,
            }
        )

    async def _token_request(self, form: dict[str, str]) -> dict[str, Any]:
        form = {**form, "client_id": self.client_id}
        auth = (self.client_id, self.client_secret) if self.client_secret else None
        _, data = await request_json(
            self.http, "POST", TOKEN, data=form, auth=auth, reauth_statuses=(400, 401)
        )
        if not isinstance(data, dict) or "access_token" not in data:
            raise ReauthRequired("token_exchange_failed")
        return data

    def _bundle(self, data: dict[str, Any], previous_refresh: str | None = None) -> dict[str, Any]:
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token") or previous_refresh,
            "expires_at": int(time.time()) + int(data.get("expires_in", 3600)) - 60,
        }

    async def link(self, user_id: UUID, credential: LinkCredential) -> LinkedSource:
        if not (credential.code and credential.code_verifier):
            raise ReauthRequired("missing_code")
        data = await self._token_request(
            {
                "grant_type": "authorization_code",
                "code": credential.code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": credential.code_verifier,
            }
        )
        bundle = self._bundle(data)
        # 403 here means the user isn't on the app's allowlist (Development Mode).
        _, me = await request_json(
            self.http,
            "GET",
            f"{API}/me",
            reauth_statuses=(401, 403),
            headers={"Authorization": f"Bearer {bundle['access_token']}"},
        )
        return LinkedSource(
            user_id=user_id,
            kind=self.kind,
            external_user_id=str((me or {}).get("id", "")),
            token_ciphertext=seal(self.cipher, bundle, user_id),
            token_key_id=self.cipher.kek_id,
            status=SourceStatus.PENDING_FIRST_PLAY,
        )

    async def refresh(self, src: LinkedSource) -> LinkedSource:
        bundle = unseal(self.cipher, src.token_ciphertext, src.user_id)
        if int(bundle.get("expires_at", 0)) > time.time():
            return src
        if not bundle.get("refresh_token"):
            raise ReauthRequired("no_refresh_token")
        data = await self._token_request(
            {"grant_type": "refresh_token", "refresh_token": str(bundle["refresh_token"])}
        )
        new = self._bundle(data, previous_refresh=str(bundle["refresh_token"]))
        return src.model_copy(update={"token_ciphertext": seal(self.cipher, new, src.user_id)})

    async def _get(self, src: LinkedSource, path: str, **params: Any) -> tuple[int, Any]:
        access = unseal(self.cipher, src.token_ciphertext, src.user_id)["access_token"]
        return await request_json(
            self.http,
            "GET",
            f"{API}{path}",
            bucket=self.bucket,
            bucket_key="rl:src:spotify",
            reauth_statuses=(401, 403),
            params=params or None,
            headers={"Authorization": f"Bearer {access}"},
        )

    async def poll_now(self, src: LinkedSource, now: datetime) -> Play | None:
        status, data = await self._get(src, "/me/player/currently-playing")
        if status == 204 or not isinstance(data, dict) or not data.get("is_playing"):
            return None
        return play_from_item(data.get("item") or {}, now)

    async def recent_plays(self, src: LinkedSource, since: datetime) -> list[Play]:
        _, data = await self._get(
            src, "/me/player/recently-played", limit=50, after=int(since.timestamp() * 1000)
        )
        out: list[Play] = []
        for it in (data or {}).get("items") or []:
            try:
                played = datetime.fromisoformat(str(it["played_at"]).replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if play := play_from_item(it.get("track") or {}, played):
                out.append(play)
        return out

    async def now_playing(self, src: LinkedSource) -> NowPlaying | None:
        play = await self.poll_now(src, datetime.now(UTC))
        if play is None:
            return None
        return NowPlaying.from_adapter(
            self, via=self.via, platform=Platform.SPOTIFY, track=play.track
        )

    async def recent(self, src: LinkedSource, since: datetime) -> list[RawListen]:
        return [
            RawListen(track=p.track, played_at=p.played_at, platform=p.platform)
            for p in await self.recent_plays(src, since)
        ]

    async def top(self, src: LinkedSource, window: Window) -> list[RawTrack]:
        _, data = await self._get(src, "/me/top/tracks", time_range=_RANGE[window], limit=50)
        return [
            p.track
            for it in (data or {}).get("items") or []
            if (p := play_from_item(it, datetime.now(UTC)))
        ]

    async def write_playlist(self, src: LinkedSource, pl: PlaylistSpec) -> str:
        raise NotSupported("Blend playlist export arrives with Blends (Sprint 8)")


__all__ = ["MAX_DIRECT_USERS", "AdapterError", "SpotifyAdapter", "pkce_pair", "play_from_item"]
