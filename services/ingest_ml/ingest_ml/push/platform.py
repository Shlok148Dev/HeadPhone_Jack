"""Which music player a pushed play came from (Tech Bible 2.4: the player, not the route)."""

from urllib.parse import parse_qs, urlsplit

from jingle_common.enums import Platform


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


def _under(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def platform_from_host(host: str) -> Platform:
    if _under(host, "spotify.com"):
        return Platform.SPOTIFY
    if _under(host, "music.apple.com"):
        return Platform.APPLE_MUSIC
    if _under(host, "youtube.com") or _under(host, "youtu.be"):
        return Platform.YOUTUBE_MUSIC
    labels = host.split(".")
    if "amazon" in labels:
        return Platform.AMAZON_MUSIC
    return Platform.UNKNOWN


def platform_from_name(name: str) -> Platform:
    n = " ".join(name.casefold().split())
    if "spotify" in n:
        return Platform.SPOTIFY
    if "apple music" in n or n == "itunes":
        return Platform.APPLE_MUSIC
    if "youtube" in n:
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
    then ``music_service_name``; else UNKNOWN (ADR-0013 order)."""
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


def safe_platform_url(url: str | None, platform: Platform) -> str | None:
    """Only https URLs on the platform's own domain become track links (no javascript:)."""
    if not url or len(url) > 800:
        return None
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    if parts.scheme != "https" or not parts.hostname:
        return None
    if platform is Platform.UNKNOWN:
        return None
    if platform_from_host(parts.hostname.casefold()) is not platform:
        return None
    return url.strip()


def external_id_from_url(url: str, platform: Platform) -> str:
    parts = urlsplit(url)
    if platform is Platform.YOUTUBE_MUSIC:
        v = parse_qs(parts.query).get("v")
        if v:
            return v[0][:200]
        if parts.hostname and parts.hostname.endswith("youtu.be"):
            return parts.path.strip("/")[:200]
    if platform is Platform.SPOTIFY and "/track/" in parts.path:
        return parts.path.rsplit("/track/", 1)[1].split("/")[0][:200]
    return ""


def spotify_url(spotify_id: str | None) -> str | None:
    """ListenBrainz ``spotify_id`` is a URL (``https://open.spotify.com/track/…``) or a bare id."""
    if not spotify_id:
        return None
    s = spotify_id.strip()
    if s.startswith("spotify:track:"):
        s = s.rsplit(":", 1)[1]
    if s.isalnum() and 10 <= len(s) <= 40:
        return f"https://open.spotify.com/track/{s}"
    return safe_platform_url(s, Platform.SPOTIFY)
