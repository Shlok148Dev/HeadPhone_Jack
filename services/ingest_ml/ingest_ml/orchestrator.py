"""Connection Orchestrator (Technical Bible 2.5; BR-13–15; ADR-0003).

One "Connect {Platform}" button; the orchestrator picks the route. Spotify: direct API when the
user is allowlisted and a Development Mode slot is free → Spotify's Last.fm link → browser
(Companion). Other platforms: browser (Companion), plus their flagged direct APIs when approved.
The user sees only the platform's own consent screen; routes are never named on cards (BR-14).
"""

import json
import logging
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from jingle_common.enums import Platform, SourceKind, SourceStatus, Via
from sqlalchemy import update

from .adapters.base import LinkCredential, LinkedSource, PollingAdapter
from .adapters.common import AdapterError, ReauthRequired
from .adapters.flagged import (
    AmazonMusicAdapter,
    AppleMusicAdapter,
    GoogleDataPortabilityAdapter,
    apple_developer_token,
)
from .adapters.lastfm import LastfmAdapter
from .adapters.listenbrainz import ListenBrainzAdapter
from .adapters.spotify import MAX_DIRECT_USERS, SpotifyAdapter, pkce_pair
from .db import now, platform_connections
from .record import STREAM, last_key, np_key
from .resources import Resources
from .sources_store import (
    count_sources,
    delete_sources,
    ensure_platform_connection,
    get_source,
    list_sources,
    save_source,
)
from .stores import LISTENS

log = logging.getLogger(__name__)

OAUTH_TTL_SECONDS = 600
POLL_ZSET = "poll:next"
FLAG_FOR_KIND = {
    SourceKind.APPLE_MUSIC: "apple_music_enabled",
    SourceKind.AMAZON_MUSIC: "amazon_music_enabled",
    SourceKind.YOUTUBE_EXPORT: "google_dataportability_enabled",
}
# Routes that belong to exactly one platform (the Companion is shared by all of them).
_PLATFORM_ROUTES = [
    SourceKind.SPOTIFY,
    SourceKind.LASTFM,
    SourceKind.LISTENBRAINZ,
    SourceKind.APPLE_MUSIC,
    SourceKind.AMAZON_MUSIC,
    SourceKind.YOUTUBE_EXPORT,
]


class ConnectError(Exception):
    """User-safe failure; ``code`` maps to the API error envelope."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ConnectPlan:
    """What the Connect sheet should do next. ``action`` is one of:

    ``redirect`` (open the platform's own consent screen at ``url``), ``browser`` (install/pair the
    Companion), ``lastfm_then_spotify`` (Last.fm consent, then one confirm inside Spotify),
    ``musickit`` (Apple's own sign-in in the browser; its Music User Token comes back to
    ``link_apple``).
    """

    action: str
    url: str | None = None
    live_on_phone: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {"action": self.action, "url": self.url, "live_on_phone": self.live_on_phone}


class Orchestrator:
    def __init__(self, res: Resources) -> None:
        self.res = res
        s = res.settings
        assert res.cipher is not None
        b = res.source_buckets
        self.listenbrainz = ListenBrainzAdapter(
            res.http, res.cipher, b["listenbrainz"], s.listenbrainz_api_url
        )
        self.lastfm = LastfmAdapter(
            res.http, res.cipher, b["lastfm"], s.lastfm_api_key, s.lastfm_shared_secret
        )
        self.spotify = SpotifyAdapter(
            res.http,
            res.cipher,
            b["spotify"],
            s.spotify_client_id,
            s.spotify_client_secret,
            s.spotify_redirect_uri,
        )

    # ---- adapters -------------------------------------------------------------------------
    def adapter(self, kind: SourceKind, flags: Mapping[str, bool]) -> PollingAdapter | None:
        flag = FLAG_FOR_KIND.get(kind)
        if flag is not None and not flags.get(flag, False):
            return None  # BR-11: approval-gated routes don't exist while their flag is off
        s, res = self.res.settings, self.res
        assert res.cipher is not None
        if kind is SourceKind.LISTENBRAINZ:
            return self.listenbrainz
        if kind is SourceKind.LASTFM:
            return self.lastfm if self.lastfm.configured else None
        if kind is SourceKind.SPOTIFY:
            return self.spotify if self.spotify.configured else None
        if kind is SourceKind.APPLE_MUSIC:
            if not (
                s.apple_music_team_id and s.apple_music_key_id and s.apple_music_private_key_path
            ):
                return None
            with open(s.apple_music_private_key_path, encoding="utf-8") as fh:
                dev = apple_developer_token(s.apple_music_team_id, s.apple_music_key_id, fh.read())
            return AppleMusicAdapter(res.http, res.cipher, res.source_buckets["apple"], dev)
        if kind is SourceKind.AMAZON_MUSIC and s.amazon_music_client_id:
            return AmazonMusicAdapter(
                res.http,
                res.cipher,
                s.amazon_music_client_id,
                s.amazon_music_client_secret,
                f"{s.public_base_url}/api/v1/sources/amazon/callback",
            )
        if kind is SourceKind.YOUTUBE_EXPORT and s.google_dataportability_client_id:
            return GoogleDataPortabilityAdapter(
                res.http,
                res.cipher,
                s.google_dataportability_client_id,
                s.google_dataportability_client_secret,
                f"{s.public_base_url}/api/v1/sources/google/callback",
            )
        return None

    # ---- OAuth state ----------------------------------------------------------------------
    async def _new_state(self, payload: dict[str, str]) -> str:
        state = secrets.token_urlsafe(24)
        await self.res.redis.set(f"oauth:{state}", json.dumps(payload), ex=OAUTH_TTL_SECONDS)
        return state

    async def _take_state(self, state: str, kind: SourceKind) -> dict[str, str]:
        raw = await self.res.redis.getdel(f"oauth:{state}")
        if not raw:
            raise ConnectError(
                "CONNECT_EXPIRED", "That took too long. Please try connecting again."
            )
        data: dict[str, str] = json.loads(raw)
        if data.get("kind") != kind.value:
            raise ConnectError(
                "CONNECT_EXPIRED", "That took too long. Please try connecting again."
            )
        return data

    # ---- start ----------------------------------------------------------------------------
    async def start(
        self, user_id: UUID, platform: Platform, *, allowlisted: bool, flags: Mapping[str, bool]
    ) -> ConnectPlan:
        await self._reenable(user_id, platform)
        if platform is Platform.SPOTIFY:
            if (
                allowlisted
                and self.spotify.configured
                and flags.get("spotify_direct_enabled", True)
                and await self._spotify_slot_free(user_id)
            ):
                verifier, challenge = pkce_pair()
                state = await self._new_state(
                    {
                        "user_id": str(user_id),
                        "platform": platform.value,
                        "kind": SourceKind.SPOTIFY.value,
                        "verifier": verifier,
                    }
                )
                return ConnectPlan(
                    "redirect", self.spotify.authorize_url(state, challenge), live_on_phone=True
                )
            if self.lastfm.configured:
                state = await self._new_state(
                    {
                        "user_id": str(user_id),
                        "platform": platform.value,
                        "kind": SourceKind.LASTFM.value,
                    }
                )
                base = self.res.settings.public_base_url
                cb = f"{base}/api/v1/sources/lastfm/callback?state={state}"
                return ConnectPlan(
                    "lastfm_then_spotify", self.lastfm.auth_url(cb), live_on_phone=True
                )
        if (
            platform is Platform.APPLE_MUSIC
            and self.adapter(SourceKind.APPLE_MUSIC, flags) is not None
        ):
            return ConnectPlan("musickit", live_on_phone=True)  # D-CONNECT-01: just log in
        return ConnectPlan("browser")

    async def _spotify_slot_free(self, user_id: UUID) -> bool:
        if await get_source(self.res.engine, user_id, SourceKind.SPOTIFY):
            return True
        return await count_sources(self.res.engine, SourceKind.SPOTIFY) < MAX_DIRECT_USERS

    async def _reenable(self, user_id: UUID, platform: Platform) -> None:
        pc = platform_connections
        async with self.res.engine.begin() as conn:
            await conn.execute(
                update(pc)
                .where(
                    pc.c.user_id == user_id,
                    pc.c.platform == platform.value,
                    pc.c.status == SourceStatus.DISABLED.value,
                )
                .values(status=SourceStatus.PENDING_FIRST_PLAY.value, updated_at=now())
            )

    # ---- complete / link ------------------------------------------------------------------
    async def _linked(self, src: LinkedSource, platform: Platform) -> LinkedSource:
        src.meta = {**src.meta, "platform": platform.value}
        saved = await save_source(self.res.engine, src)
        await ensure_platform_connection(
            self.res.engine, src.user_id, platform, SourceStatus.PENDING_FIRST_PLAY
        )
        await self.res.redis.zadd(POLL_ZSET, {str(saved.id): 0})  # poll right away
        return saved

    async def complete_spotify(self, state: str, code: str) -> tuple[UUID, Platform]:
        data = await self._take_state(state, SourceKind.SPOTIFY)
        user_id = UUID(data["user_id"])
        try:
            src = await self.spotify.link(
                user_id, LinkCredential(code=code, code_verifier=data["verifier"])
            )
        except ReauthRequired as exc:
            # 403 = not on the Development Mode allowlist: fall back silently (BR-15).
            raise ConnectError(
                "SPOTIFY_NOT_AVAILABLE",
                "Spotify didn't let Jingle connect directly. Continue in your browser instead.",
            ) from exc
        await self._linked(src, Platform.SPOTIFY)
        return user_id, Platform.SPOTIFY

    async def complete_lastfm(self, state: str, token: str) -> tuple[UUID, Platform]:
        data = await self._take_state(state, SourceKind.LASTFM)
        user_id, platform = UUID(data["user_id"]), Platform(data["platform"])
        try:
            src = await self.lastfm.link(user_id, LinkCredential(token=token))
        except (ReauthRequired, AdapterError) as exc:
            raise ConnectError("LASTFM_FAILED", "We couldn't connect Last.fm. Try again.") from exc
        await self._linked(src, platform)
        return user_id, platform

    async def link_listenbrainz(self, user_id: UUID, platform: Platform, token: str) -> None:
        try:
            src = await self.listenbrainz.link(user_id, LinkCredential(token=token.strip()))
        except ReauthRequired as exc:
            # SRS JNG-01-02 failure path: exact copy, and no source record is created.
            raise ConnectError(
                "TOKEN_INVALID", "That token didn't work — copy it again from ListenBrainz settings"
            ) from exc
        await self._linked(src, platform)

    async def link_lastfm_username(self, user_id: UUID, platform: Platform, username: str) -> None:
        try:
            src = await self.lastfm.link(user_id, LinkCredential(username=username.strip()))
        except ReauthRequired as exc:
            msg = (
                "That Last.fm profile is private. Make it public or connect with Last.fm sign-in."
                if exc.reason == "private_profile"
                else "We couldn't find that Last.fm user."
            )
            raise ConnectError("LASTFM_FAILED", msg) from exc
        await self._linked(src, platform)

    async def link_apple(
        self, user_id: UUID, music_user_token: str, flags: Mapping[str, bool]
    ) -> None:
        """Apple Music: the browser's MusicKit sign-in returns a Music User Token; it's sealed
        (AES-256-GCM) like every other credential and polled for recent plays."""
        adapter = self.adapter(SourceKind.APPLE_MUSIC, flags)
        if adapter is None:
            raise ConnectError("NOT_CONFIGURED", "Apple Music isn't set up on this Jingle yet.")
        try:
            src = await adapter.link(user_id, LinkCredential(token=music_user_token.strip()))
        except ReauthRequired as exc:
            raise ConnectError(
                "APPLE_FAILED", "Apple Music sign-in didn't finish. Try again."
            ) from exc
        await self._linked(src, Platform.APPLE_MUSIC)

    # ---- unlink ---------------------------------------------------------------------------
    async def unlink(self, user_id: UUID, platform: Platform) -> None:
        """JNG-01-09: remove one platform's routes; others keep working. Direct-Spotify data is
        erased at once (ADR-0007); other history stays (it is the user's listening)."""
        engine = self.res.engine
        kinds = [
            s.kind
            for s in await list_sources(engine, _PLATFORM_ROUTES)
            if s.user_id == user_id and s.meta.get("platform") == platform.value
        ]
        if SourceKind.SPOTIFY in kinds:
            await self.purge_direct_spotify(user_id)
        for kind in kinds:
            src = await get_source(engine, user_id, kind)
            if src:
                await self.res.redis.zrem(POLL_ZSET, str(src.id))
        await delete_sources(engine, user_id, kinds)
        pc = platform_connections
        async with engine.begin() as conn:  # DISABLED: the Companion won't re-enable it on push
            await conn.execute(
                update(pc)
                .where(pc.c.user_id == user_id, pc.c.platform == platform.value)
                .values(status=SourceStatus.DISABLED.value, updated_at=now())
            )

    async def purge_direct_spotify(self, user_id: UUID) -> None:
        """Delete every Spotify-API-sourced record for the user now (BR-03 allows 24 h)."""
        uid = str(user_id)
        await self.res.mongo[LISTENS].delete_many(
            {
                "meta.user_id": uid,
                "meta.via": Via.DIRECT.value,
                "meta.platform": Platform.SPOTIFY.value,
            }
        )
        for key in (np_key(user_id), last_key(user_id)):
            if (await self.res.redis.hget(key, "via")) == Via.DIRECT.value:
                await self.res.redis.delete(key)
        marker = f'"user_id":"{uid}"'
        drop: list[Any] = []
        for entry_id, fields in (await self.res.redis.xrange(STREAM)) or []:
            data = (fields or {}).get("data") or ""
            compact = data.replace(" ", "") if isinstance(data, str) else ""
            if (
                marker in compact
                and '"via":"DIRECT"' in compact
                and '"platform":"SPOTIFY"' in compact
            ):
                drop.append(entry_id)
        if drop:
            await self.res.redis.xdel(STREAM, *drop)
        log.info("purged direct Spotify data for a user")
