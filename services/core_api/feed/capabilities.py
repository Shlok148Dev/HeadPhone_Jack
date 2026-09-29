"""Honest per-platform capabilities for Settings -> Connections (BR-13, BR-15; PLAN rule 9).

The user sees platforms and what works, never the routes behind them (BR-14). In the web phase,
phone listening on YouTube Music, Apple Music and Amazon Music shows as Recent only.
"""

from __future__ import annotations

from sources.models import Platform, SourceKind, SourceStatus

# Routes that capture Spotify plays on any device (phone included).
_SPOTIFY_ANY_DEVICE = {SourceKind.SPOTIFY, SourceKind.LASTFM, SourceKind.LISTENBRAINZ}

NOTES = {
    Platform.SPOTIFY: "",
    Platform.YOUTUBE_MUSIC: (
        "Live works while you listen in your browser. Phone listening shows up as Recent."
    ),
    Platform.APPLE_MUSIC: (
        "Live works while you listen in your browser. Phone listening shows up as Recent."
    ),
    Platform.AMAZON_MUSIC: (
        "Live works while you listen in your browser. Phone listening shows up as Recent."
    ),
    Platform.UNKNOWN: "",
}


def capabilities(
    platform: str, status: str, active_kinds: set[str], has_companion: bool
) -> dict[str, bool]:
    usable = status not in (SourceStatus.DISABLED, SourceStatus.ERROR, SourceStatus.NEEDS_REAUTH)
    if not usable or platform == Platform.UNKNOWN:
        return {"live_on_web": False, "live_on_phone": False, "history": False}
    if platform == Platform.SPOTIFY:
        any_device = bool(active_kinds & _SPOTIFY_ANY_DEVICE)
        return {
            "live_on_web": has_companion or any_device,
            "live_on_phone": any_device,
            "history": True,
        }
    # YouTube Music, Apple Music, Amazon Music: Live only via the browser companion (web phase).
    return {"live_on_web": has_companion, "live_on_phone": False, "history": True}
