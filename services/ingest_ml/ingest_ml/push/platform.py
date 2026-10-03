"""Which music player a pushed play came from (Tech Bible 2.4: the player, not the route),
and which pushed URLs may become shared "Open in …" links.

Host matching is by exact allowlist. Plain YouTube (www.youtube.com) is not YouTube Music and
maps to UNKNOWN.
"""

import re
from urllib.parse import parse_qs, urlsplit

from jingle_common.enums import Platform

_AMAZON_TLDS = (
    "com",
    "in",
    "co.uk",
    "de",
    "fr",
    "it",
    "es",
    "ca",
    "com.au",
    "co.jp",
    "com.br",
    "com.mx",
)
AMAZON_MUSIC_HOSTS = frozenset(f"music.amazon.{tld}" for tld in _AMAZON_TLDS)

# Hosts that identify the player (inference only; never used to build links).
_INFER_HOSTS: dict[Platform, frozenset[str]] = {
    Platform.SPOTIFY: frozenset({"spotify.com", "open.spotify.com", "play.spotify.com"}),
    Platform.APPLE_MUSIC: frozenset({"music.apple.com"}),
    Platform.YOUTUBE_MUSIC: frozenset({"music.youtube.com"}),
    # ListenBrainz clients may send the bare store domain as music_service (inference only)
    Platform.AMAZON_MUSIC: AMAZON_MUSIC_HOSTS | frozenset(f"amazon.{tld}" for tld in _AMAZON_TLDS),
}

# Hosts a stored track link may point at (shared catalog; see SEC H1).
LINK_HOSTS: dict[Platform, frozenset[str]] = {
    Platform.SPOTIFY: frozenset({"open.spotify.com"}),
    Platform.APPLE_MUSIC: frozenset({"music.apple.com"}),
    Platform.YOUTUBE_MUSIC: frozenset({"music.youtube.com"}),
    Platform.AMAZON_MUSIC: AMAZON_MUSIC_HOSTS,
}

_SAFE_PATH = re.compile(r"^/[A-Za-z0-9/_\-.~%]*$")
_YT_ID = re.compile(r"^[A-Za-z0-9_-]{6,20}$")
_SPOTIFY_ID = re.compile(r"^[A-Za-z0-9]{10,40}$")
_APPLE_TRACK = re.compile(r"^\d{1,20}$")


def _host(value: str) -> str | None:
    v = value.strip().casefold()
    if not v:
        return None
    if "://" not in v:
        if "." not in v or " " in v:
            return None
        v = "https://" + v
    try:
        host = urlsplit(v).hostname
    except ValueError:
        return None
    return host or None


def platform_from_host(host: str) -> Platform:
    host = host.casefold()
    for platform, hosts in _INFER_HOSTS.items():
        if host in hosts:
            return platform
    return Platform.UNKNOWN


def platform_from_name(name: str) -> Platform:
    n = " ".join(name.casefold().split())
    if "spotify" in n:
        return Platform.SPOTIFY
    if "apple music" in n or n == "itunes":
        return Platform.APPLE_MUSIC
    if "youtube music" in n:
        return Platform.YOUTUBE_MUSIC
    if "amazon" in n:
        return Platform.AMAZON_MUSIC
    return Platform.UNKNOWN


def infer_platform(
    music_service: str | None = None,
    origin_url: str | None = None,
    music_service_name: str | None = None,
) -> Platform:
    """``origin_url`` host, then ``music_service`` (a domain in ListenBrainz, sometimes a name),
    then ``music_service_name``; else UNKNOWN (ADR-0014 order)."""
    if origin_url and (host := _host(origin_url)):
        p = platform_from_host(host)
        if p is not Platform.UNKNOWN:
            return p
    if music_service:
        host = _host(music_service)
        p = platform_from_host(host) if host else platform_from_name(music_service)
        if p is not Platform.UNKNOWN:
            return p
    if music_service_name:
        return platform_from_name(music_service_name)
    return Platform.UNKNOWN


def _has_forbidden_chars(url: str) -> bool:
    return any(c == "\\" or c.isspace() or ord(c) < 0x20 or ord(c) == 0x7F for c in url)


def safe_platform_url(url: str | None, platform: Platform) -> str | None:
    """Return a server-rebuilt canonical https URL for ``platform``, or None.

    Rejects backslashes, whitespace/control characters, userinfo, explicit ports and any host
    outside the platform's exact allowlist. The input string itself is never stored.
    """
    if not url or len(url) > 800 or platform is Platform.UNKNOWN:
        return None
    if _has_forbidden_chars(url):
        return None
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme != "https" or "@" in parts.netloc or port is not None:
        return None
    host = (parts.hostname or "").casefold()
    if host not in LINK_HOSTS.get(platform, frozenset()):
        return None
    path = parts.path or "/"
    if not _SAFE_PATH.match(path):
        return None
    if platform is Platform.YOUTUBE_MUSIC:
        vid = (parse_qs(parts.query).get("v") or [""])[0]
        return f"https://{host}/watch?v={vid}" if _YT_ID.match(vid) else None
    if platform is Platform.APPLE_MUSIC:
        track = (parse_qs(parts.query).get("i") or [""])[0]
        if _APPLE_TRACK.match(track):
            return f"https://{host}{path}?i={track}"
    return f"https://{host}{path}"


def external_id_from_url(url: str, platform: Platform) -> str:
    parts = urlsplit(url)
    if platform is Platform.YOUTUBE_MUSIC:
        v = parse_qs(parts.query).get("v")
        return v[0][:200] if v else ""
    if platform is Platform.SPOTIFY and "/track/" in parts.path:
        return parts.path.rsplit("/track/", 1)[1].split("/")[0][:200]
    if platform is Platform.APPLE_MUSIC:
        i = parse_qs(parts.query).get("i")
        return i[0][:200] if i else ""
    return ""


def spotify_url(spotify_id: str | None) -> str | None:
    """ListenBrainz ``spotify_id`` is a URL (``https://open.spotify.com/track/…``) or a bare id."""
    if not spotify_id:
        return None
    s = spotify_id.strip()
    if s.startswith("spotify:track:"):
        s = s.rsplit(":", 1)[1]
    if _SPOTIFY_ID.match(s):
        return f"https://open.spotify.com/track/{s}"
    return safe_platform_url(s, Platform.SPOTIFY)
