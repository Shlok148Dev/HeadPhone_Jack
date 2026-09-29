"""Enumerations shared by every service. Spelling is fixed by docs/architecture/CONTRACTS.md §4."""

from enum import StrEnum


class Platform(StrEnum):
    SPOTIFY = "SPOTIFY"
    APPLE_MUSIC = "APPLE_MUSIC"
    AMAZON_MUSIC = "AMAZON_MUSIC"
    YOUTUBE_MUSIC = "YOUTUBE_MUSIC"
    UNKNOWN = "UNKNOWN"


class Via(StrEnum):
    """How Jingle learned about a play. Internal only: never sent to clients (ADR-0002)."""

    DIRECT = "DIRECT"
    LISTENBRAINZ = "LISTENBRAINZ"
    LASTFM = "LASTFM"
    EXPORT = "EXPORT"
    COMPANION = "COMPANION"


class SourceKind(StrEnum):
    LISTENBRAINZ = "LISTENBRAINZ"
    LASTFM = "LASTFM"
    APPLE_MUSIC = "APPLE_MUSIC"
    SPOTIFY = "SPOTIFY"
    AMAZON_MUSIC = "AMAZON_MUSIC"
    YOUTUBE_EXPORT = "YOUTUBE_EXPORT"
    COMPANION = "COMPANION"


class CardState(StrEnum):
    LIVE = "LIVE"
    RECENT = "RECENT"
    TOP = "TOP"
    HIDDEN = "HIDDEN"


class EventKind(StrEnum):
    NOW_PLAYING = "NOW_PLAYING"
    LISTEN = "LISTEN"


class SourceStatus(StrEnum):
    CONNECTED = "CONNECTED"
    NEEDS_REAUTH = "NEEDS_REAUTH"
    PENDING_FIRST_PLAY = "PENDING_FIRST_PLAY"
    ERROR = "ERROR"
    DISABLED = "DISABLED"


LIVE_CAPABLE_ROUTES: frozenset[Via] = frozenset(
    {Via.COMPANION, Via.LISTENBRAINZ, Via.LASTFM, Via.DIRECT}
)
"""Routes that may produce a Live state (BR-01). DIRECT counts only for Spotify; see is_live_capable."""

LIVE_MAX_AGE_SECONDS = 90

PLATFORM_DISPLAY_NAMES: dict[Platform, str] = {
    Platform.SPOTIFY: "Spotify",
    Platform.APPLE_MUSIC: "Apple Music",
    Platform.AMAZON_MUSIC: "Amazon Music",
    Platform.YOUTUBE_MUSIC: "YouTube Music",
    Platform.UNKNOWN: "",
}


def is_live_capable(via: Via, platform: Platform) -> bool:
    """True if an event from this route and platform may ever render as Live (BR-01)."""
    if via is Via.DIRECT:
        return platform is Platform.SPOTIFY
    return via in LIVE_CAPABLE_ROUTES
