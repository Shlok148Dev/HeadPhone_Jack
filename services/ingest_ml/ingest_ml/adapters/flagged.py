"""Approval-gated adapters, built but loaded only when their flag is on (ADR-0001).

* Apple Music (``apple_music_enabled``): MusicKit developer JWT (ES256) + Music User Token.
  Recently played has no timestamps, so plays are ``played_at_estimated`` and only new items at
  the top of the list are recorded (ADR-0016). Never Live (C-04).
* Amazon Music (``amazon_music_enabled``): Login with Amazon + ``x-api-key``; the V2 closed beta
  documents library/playlists only, so recent/top/live are NotSupported.
* Google Data Portability (``google_dataportability_enabled``): EEA/UK only (ADR-0015); starts a
  ``myactivity.youtube`` archive job and parses the result like a Takeout upload.
"""

import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
import jwt
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

APPLE_API = "https://api.music.apple.com/v1"


def apple_developer_token(
    team_id: str, key_id: str, private_key_pem: str, ttl_days: int = 90
) -> str:
    now = int(time.time())
    return jwt.encode(
        {"iss": team_id, "iat": now, "exp": now + ttl_days * 86400},
        private_key_pem,
        algorithm="ES256",
        headers={"kid": key_id},
    )


def _apple_artwork(attrs: dict[str, Any]) -> str | None:
    url = (attrs.get("artwork") or {}).get("url")
    if isinstance(url, str) and url.startswith("https://") and "mzstatic.com" in url:
        return url.replace("{w}", "300").replace("{h}", "300")
    return None


class AppleMusicAdapter:
    kind = SourceKind.APPLE_MUSIC
    via = Via.DIRECT
    caps = Capabilities(live=False, recent=True, top=True, playlist_write=True, trainable=True)

    def __init__(
        self,
        http: httpx.AsyncClient,
        cipher: TokenCipher,
        bucket: TokenBucket,
        developer_token: str,
    ) -> None:
        self.http, self.cipher, self.bucket, self.dev = http, cipher, bucket, developer_token

    async def _get(self, src: LinkedSource, path: str, **params: Any) -> Any:
        mut = unseal(self.cipher, src.token_ciphertext, src.user_id)["music_user_token"]
        _, data = await request_json(
            self.http,
            "GET",
            f"{APPLE_API}{path}",
            bucket=self.bucket,
            bucket_key="rl:src:apple",
            reauth_statuses=(401, 403),
            params=params or None,
            headers={"Authorization": f"Bearer {self.dev}", "Music-User-Token": mut},
        )
        return data

    async def link(self, user_id: UUID, credential: LinkCredential) -> LinkedSource:
        if not credential.token:
            raise ReauthRequired("missing_music_user_token")
        return LinkedSource(
            user_id=user_id,
            kind=self.kind,
            token_ciphertext=seal(self.cipher, {"music_user_token": credential.token}, user_id),
            token_key_id=self.cipher.kek_id,
            status=SourceStatus.PENDING_FIRST_PLAY,
        )

    async def refresh(self, src: LinkedSource) -> LinkedSource:
        return src

    async def poll_now(self, src: LinkedSource, now: datetime) -> Play | None:
        raise NotSupported("Apple Music has no now-playing endpoint")

    async def recent_plays(self, src: LinkedSource, since: datetime) -> list[Play]:
        data = await self._get(src, "/me/recent/played/tracks", limit=30)
        items = (data or {}).get("data") or []
        seen = set(src.meta.get("seen_ids") or [])
        out: list[Play] = []
        now = datetime.now(UTC)
        for it in items:  # newest first; stop at the first item already recorded
            if it.get("id") in seen:
                break
            a = it.get("attributes") or {}
            if not a.get("artistName") or not a.get("name"):
                continue
            out.append(
                Play(
                    track=RawTrack(
                        artist=a["artistName"],
                        title=a["name"],
                        album=a.get("albumName"),
                        duration_ms=a.get("durationInMillis"),
                    ),
                    played_at=now,
                    platform=Platform.APPLE_MUSIC,
                    isrc=a.get("isrc"),
                    artwork_url=_apple_artwork(a),
                    played_at_estimated=True,
                )
            )
        src.meta["seen_ids"] = [it.get("id") for it in items[:30]]
        return out

    async def now_playing(self, src: LinkedSource) -> NowPlaying | None:
        raise NotSupported("Apple Music cannot report now-playing")

    async def recent(self, src: LinkedSource, since: datetime) -> list[RawListen]:
        return [
            RawListen(track=p.track, played_at=p.played_at, platform=p.platform, isrc=p.isrc)
            for p in await self.recent_plays(src, since)
        ]

    async def top(self, src: LinkedSource, window: Window) -> list[RawTrack]:
        data = await self._get(src, "/me/history/heavy-rotation", limit=25)
        return [
            RawTrack(
                artist=(d.get("attributes") or {}).get("artistName", ""),
                title=(d.get("attributes") or {}).get("name", ""),
            )
            for d in (data or {}).get("data") or []
            if (d.get("attributes") or {}).get("name")
        ]

    async def write_playlist(self, src: LinkedSource, pl: PlaylistSpec) -> str:
        raise NotSupported("Blend playlist export arrives with Blends (Sprint 8)")


class AmazonMusicAdapter:
    kind = SourceKind.AMAZON_MUSIC
    via = Via.DIRECT
    caps = Capabilities(live=False, recent=False, top=False, playlist_write=True, trainable=True)
    TOKEN_URL = "https://api.amazon.com/auth/o2/token"  # noqa: S105 - URL

    def __init__(
        self,
        http: httpx.AsyncClient,
        cipher: TokenCipher,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> None:
        self.http, self.cipher = http, cipher
        self.client_id, self.client_secret, self.redirect_uri = (
            client_id,
            client_secret,
            redirect_uri,
        )

    async def link(self, user_id: UUID, credential: LinkCredential) -> LinkedSource:
        if not credential.code:
            raise ReauthRequired("missing_code")
        _, data = await request_json(
            self.http,
            "POST",
            self.TOKEN_URL,
            reauth_statuses=(400, 401),
            data={
                "grant_type": "authorization_code",
                "code": credential.code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        if not isinstance(data, dict) or "access_token" not in data:
            raise ReauthRequired("token_exchange_failed")
        bundle = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_at": int(time.time()) + int(data.get("expires_in", 3600)) - 60,
        }
        return LinkedSource(
            user_id=user_id,
            kind=self.kind,
            token_ciphertext=seal(self.cipher, bundle, user_id),
            token_key_id=self.cipher.kek_id,
            status=SourceStatus.CONNECTED,
        )

    async def refresh(self, src: LinkedSource) -> LinkedSource:
        return src

    async def poll_now(self, src: LinkedSource, now: datetime) -> Play | None:
        raise NotSupported("Amazon Music exposes no now-playing")

    async def recent_plays(self, src: LinkedSource, since: datetime) -> list[Play]:
        raise NotSupported("Amazon Music V2 documents no listening history")

    async def now_playing(self, src: LinkedSource) -> NowPlaying | None:
        raise NotSupported("Amazon Music cannot report now-playing")

    async def recent(self, src: LinkedSource, since: datetime) -> list[RawListen]:
        raise NotSupported("Amazon Music V2 documents no listening history")

    async def top(self, src: LinkedSource, window: Window) -> list[RawTrack]:
        raise NotSupported("Amazon Music V2 documents no top tracks")

    async def write_playlist(self, src: LinkedSource, pl: PlaylistSpec) -> str:
        raise NotSupported("Blend playlist export arrives with Blends (Sprint 8)")


class GoogleDataPortabilityAdapter:
    """Automatic YouTube history (JNG-01-07). The archive is parsed like a Takeout upload."""

    kind = SourceKind.YOUTUBE_EXPORT
    via = Via.EXPORT
    caps = Capabilities(live=False, recent=True, top=False, playlist_write=False, trainable=True)
    API = "https://dataportability.googleapis.com/v1"
    TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 - URL
    SCOPE = "https://www.googleapis.com/auth/dataportability.myactivity.youtube"

    def __init__(
        self,
        http: httpx.AsyncClient,
        cipher: TokenCipher,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> None:
        self.http, self.cipher = http, cipher
        self.client_id, self.client_secret, self.redirect_uri = (
            client_id,
            client_secret,
            redirect_uri,
        )

    async def link(self, user_id: UUID, credential: LinkCredential) -> LinkedSource:
        if not credential.code:
            raise ReauthRequired("missing_code")
        _, data = await request_json(
            self.http,
            "POST",
            self.TOKEN_URL,
            reauth_statuses=(400, 401),
            data={
                "grant_type": "authorization_code",
                "code": credential.code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        if not isinstance(data, dict) or "access_token" not in data:
            raise ReauthRequired("token_exchange_failed")
        return LinkedSource(
            user_id=user_id,
            kind=self.kind,
            token_ciphertext=seal(
                self.cipher,
                {"access_token": data["access_token"], "refresh_token": data.get("refresh_token")},
                user_id,
            ),
            token_key_id=self.cipher.kek_id,
            status=SourceStatus.PENDING_FIRST_PLAY,
        )

    async def refresh(self, src: LinkedSource) -> LinkedSource:
        return src

    async def start_archive(self, src: LinkedSource) -> str:
        token = unseal(self.cipher, src.token_ciphertext, src.user_id)["access_token"]
        _, data = await request_json(
            self.http,
            "POST",
            f"{self.API}/portabilityArchive:initiate",
            reauth_statuses=(401, 403),
            json={"resources": ["myactivity.youtube"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        job = (data or {}).get("archiveJobId")
        if not job:
            raise AdapterError("archive job not started")
        return str(job)

    async def archive_urls(self, src: LinkedSource, job_id: str) -> list[str] | None:
        token = unseal(self.cipher, src.token_ciphertext, src.user_id)["access_token"]
        _, data = await request_json(
            self.http,
            "GET",
            f"{self.API}/archiveJobs/{job_id}/portabilityArchiveState",
            reauth_statuses=(401, 403),
            headers={"Authorization": f"Bearer {token}"},
        )
        if (data or {}).get("state") != "COMPLETE":
            return None
        return [
            u
            for u in (data or {}).get("urls") or []
            if isinstance(u, str) and u.startswith("https://")
        ]

    async def poll_now(self, src: LinkedSource, now: datetime) -> Play | None:
        raise NotSupported("exports are never live")

    async def recent_plays(self, src: LinkedSource, since: datetime) -> list[Play]:
        return []  # delivered by the archive job workflow, not by polling

    async def now_playing(self, src: LinkedSource) -> NowPlaying | None:
        raise NotSupported("exports are never live")

    async def recent(self, src: LinkedSource, since: datetime) -> list[RawListen]:
        return []

    async def top(self, src: LinkedSource, window: Window) -> list[RawTrack]:
        raise NotSupported("derived from history, not fetched")

    async def write_playlist(self, src: LinkedSource, pl: PlaylistSpec) -> str:
        raise NotSupported("YouTube history is read-only")
