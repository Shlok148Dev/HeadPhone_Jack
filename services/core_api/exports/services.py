"""Exporters' server side (D-EXPORT-01).

- ``config()``: which apps can take a playlist right now (keys present), plus public client ids.
- ``apple_developer_token()``: the MusicKit developer token (ES256, signed with Jingle's key).
- ``youtube_matches()``: YouTube video ids for songs, searched by the server with Jingle's API key
  (official YouTube Data API), cached forever per song. Clients never write matches.
"""

from __future__ import annotations

import logging
import re
import time

import httpx
from django.conf import settings

from .models import TrackMatch

log = logging.getLogger(__name__)

YOUTUBE_SEARCH = "https://www.googleapis.com/youtube/v3/search"
APPLE_TOKEN_KEY = "exports:apple:devtoken"
APPLE_TOKEN_TTL = 12 * 3600
MAX_MATCH_BATCH = 50
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def apple_enabled() -> bool:
    return bool(
        settings.APPLE_MUSIC_TEAM_ID
        and settings.APPLE_MUSIC_KEY_ID
        and settings.APPLE_MUSIC_PRIVATE_KEY_PATH
    )


def config() -> dict:
    return {
        "spotify": {
            "enabled": bool(settings.SPOTIFY_CLIENT_ID),
            "client_id": settings.SPOTIFY_CLIENT_ID or None,  # public by design (PKCE, no secret)
        },
        "youtube_music": {
            "enabled": bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.YOUTUBE_API_KEY),
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID or None,
        },
        "apple_music": {"enabled": apple_enabled()},
        "amazon_music": {
            "enabled": False,
            "reason": "Amazon Music doesn't let apps create playlists.",
        },
    }


def apple_developer_token() -> str:
    """MusicKit developer token: ES256 JWT {iss: team, iat, exp}, header kid. Cached 12 h."""
    import jwt

    from core_api.redis_client import get_redis

    r = get_redis()
    cached = r.get(APPLE_TOKEN_KEY)
    if cached:
        return cached
    with open(settings.APPLE_MUSIC_PRIVATE_KEY_PATH, encoding="utf-8") as f:
        key = f.read()
    now = int(time.time())
    token = jwt.encode(
        {"iss": settings.APPLE_MUSIC_TEAM_ID, "iat": now, "exp": now + APPLE_TOKEN_TTL + 3600},
        key,
        algorithm="ES256",
        headers={"kid": settings.APPLE_MUSIC_KEY_ID},
    )
    r.setex(APPLE_TOKEN_KEY, APPLE_TOKEN_TTL, token)
    return token


def _pick_video(items: list[dict], title: str, artist: str) -> str | None:
    """Prefer YouTube's official audio ("Artist - Topic" channels: what YouTube Music plays), then a
    title match by the right artist, then the first music result."""
    from artwork.services import norm

    t, a = norm(title), norm(artist)

    def vid(it):
        v = (it.get("id") or {}).get("videoId") or ""
        return v if _VIDEO_ID.match(v) else None

    def sn(it):
        return it.get("snippet") or {}

    for it in items:
        ch = norm(sn(it).get("channelTitle", ""))
        if ch.endswith("topic") and a.split(" ")[0] in ch and t in norm(sn(it).get("title", "")):
            return vid(it)
    for it in items:
        st = norm(sn(it).get("title", ""))
        if t in st and (a in st or a in norm(sn(it).get("channelTitle", ""))):
            return vid(it)
    return vid(items[0]) if items else None


def youtube_matches(songs: list[dict], client: httpx.Client | None = None) -> dict[str, str | None]:
    """{track_key: video id or None} for [{key, title, artist}], from cache or a server search."""
    songs = songs[:MAX_MATCH_BATCH]
    keys = [s["key"] for s in songs]
    known = {
        m.track_key: m.external_id or None
        for m in TrackMatch.objects.filter(platform="youtube_music", track_key__in=keys)
    }
    out: dict[str, str | None] = dict(known)
    todo = [s for s in songs if s["key"] not in known]
    if not todo or not settings.YOUTUBE_API_KEY:
        return {k: out.get(k) for k in keys}
    own = client is None
    client = client or httpx.Client(timeout=8)
    try:
        for s in todo:
            try:
                r = client.get(
                    YOUTUBE_SEARCH,
                    params={
                        "part": "snippet",
                        "q": f"{s['artist']} {s['title']}",
                        "type": "video",
                        "videoCategoryId": "10",  # Music
                        "maxResults": 5,
                        "key": settings.YOUTUBE_API_KEY,
                    },
                )
                if r.status_code == 403:  # daily quota spent: stop, retry tomorrow (nothing cached)
                    log.warning("youtube quota exhausted")
                    break
                r.raise_for_status()
                vid = _pick_video(r.json().get("items") or [], s["title"], s["artist"])
            except httpx.HTTPError:
                log.warning("youtube search failed")
                continue
            TrackMatch.objects.update_or_create(
                platform="youtube_music", track_key=s["key"], defaults={"external_id": vid or ""}
            )
            out[s["key"]] = vid
    finally:
        if own:
            client.close()
    return {k: out.get(k) for k in keys}
