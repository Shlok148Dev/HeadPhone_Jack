"""Player platform inference and trainable flags."""

import pytest
from jingle_common.enums import Platform, Via
from jingle_common.events import default_trainable

from ingest_ml.push.platform import (
    external_id_from_url,
    infer_platform,
    safe_platform_url,
    spotify_url,
)

P = Platform

TABLE = [
    # (music_service, origin_url, music_service_name, expected)
    ("spotify.com", None, None, P.SPOTIFY),
    ("open.spotify.com", None, None, P.SPOTIFY),
    (None, "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh", None, P.SPOTIFY),
    ("music.apple.com", None, None, P.APPLE_MUSIC),
    (None, "https://music.apple.com/in/album/x/123?i=456", None, P.APPLE_MUSIC),
    ("music.youtube.com", None, None, P.YOUTUBE_MUSIC),
    # plain YouTube is not YouTube Music (Orchestrator decision, S1-INGEST review)
    ("youtube.com", None, None, P.UNKNOWN),
    (None, "https://www.youtube.com/watch?v=abc", None, P.UNKNOWN),
    ("music.amazon.in", None, None, P.AMAZON_MUSIC),
    (None, "https://music.amazon.com/albums/B0", None, P.AMAZON_MUSIC),
    ("amazon.co.uk", None, None, P.AMAZON_MUSIC),
    (None, None, "Spotify", P.SPOTIFY),
    (None, None, "YouTube Music", P.YOUTUBE_MUSIC),
    (None, None, "Apple Music", P.APPLE_MUSIC),
    (None, None, "Amazon Music", P.AMAZON_MUSIC),
    ("Spotify", None, None, P.SPOTIFY),  # some clients send a name, not a domain
    ("soundcloud.com", None, None, P.UNKNOWN),
    (None, "https://example.com/spotify.com", None, P.UNKNOWN),
    (None, "https://notspotify.com/x", None, P.UNKNOWN),
    (None, None, "Winamp", P.UNKNOWN),
    (None, None, None, P.UNKNOWN),
    # origin_url wins over music_service (ADR-0013 order)
    ("spotify.com", "https://music.youtube.com/watch?v=1", None, P.YOUTUBE_MUSIC),
    # unknown origin_url falls through to music_service, then the name
    ("music.apple.com", "https://example.com", "Spotify", P.APPLE_MUSIC),
    ("unknown.example", "https://example.com", "Spotify", P.SPOTIFY),
]


@pytest.mark.parametrize(("service", "origin", "name", "expected"), TABLE)
def test_infer_platform(
    service: str | None, origin: str | None, name: str | None, expected: Platform
) -> None:
    assert infer_platform(service, origin, name) is expected


def test_safe_platform_url() -> None:
    assert (
        safe_platform_url(
            "https://music.youtube.com/watch?v=dQw4w9WgXcQ&si=tracker", P.YOUTUBE_MUSIC
        )
        == "https://music.youtube.com/watch?v=dQw4w9WgXcQ"
    )
    assert safe_platform_url("https://music.youtube.com/watch?v=x", P.YOUTUBE_MUSIC) is None
    assert safe_platform_url("http://music.youtube.com/watch?v=x", P.YOUTUBE_MUSIC) is None
    assert safe_platform_url("javascript:alert(1)", P.YOUTUBE_MUSIC) is None
    assert safe_platform_url("https://evil.com/?music.youtube.com", P.YOUTUBE_MUSIC) is None
    assert safe_platform_url("https://open.spotify.com/track/1", P.YOUTUBE_MUSIC) is None
    assert safe_platform_url("https://x.com", P.UNKNOWN) is None
    assert safe_platform_url("https://" + "a" * 800, P.SPOTIFY) is None
    assert safe_platform_url(None, P.SPOTIFY) is None


def test_spotify_url_and_ids() -> None:
    assert (
        spotify_url("4iV5W9uYEdYUVa79Axb7Rh")
        == "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"
    )
    assert spotify_url(
        "spotify:track:4iV5W9uYEdYUVa79Axb7Rh",
    ).endswith("/4iV5W9uYEdYUVa79Axb7Rh")  # type: ignore[union-attr]
    assert spotify_url("https://open.spotify.com/track/abc") == "https://open.spotify.com/track/abc"
    assert spotify_url("https://evil.com/track/abc") is None
    assert spotify_url(None) is None
    assert external_id_from_url("https://music.youtube.com/watch?v=xyz", P.YOUTUBE_MUSIC) == "xyz"
    assert external_id_from_url("https://open.spotify.com/track/abc/", P.SPOTIFY) == "abc"
    assert external_id_from_url("https://music.apple.com/x", P.APPLE_MUSIC) == ""


@pytest.mark.parametrize(
    ("via", "platform", "trainable"),
    [
        (Via.COMPANION, P.SPOTIFY, True),  # Companion capture is not Spotify API data (ADR-0007)
        (Via.COMPANION, P.YOUTUBE_MUSIC, True),
        (Via.DIRECT, P.SPOTIFY, False),
        (Via.LASTFM, P.SPOTIFY, False),
        (Via.LISTENBRAINZ, P.APPLE_MUSIC, True),
    ],
)
def test_trainable_flags(via: Via, platform: Platform, trainable: bool) -> None:
    assert default_trainable(via, platform) is trainable


@pytest.mark.parametrize(
    ("url", "platform"),
    [
        ("https://evil.com\@open.spotify.com/track/abc", P.SPOTIFY),  # backslash trick
        ("https://user@open.spotify.com/track/abc", P.SPOTIFY),  # userinfo
        ("https://open.spotify.com:8443/track/abc", P.SPOTIFY),  # explicit port
        ("https://amazon.evil.com/x", P.AMAZON_MUSIC),  # label match must not pass
        ("https://music.amazon.evil.com/x", P.AMAZON_MUSIC),
        ("https://open.spotify.com/track/a" + chr(10) + "b", P.SPOTIFY),  # control char
        ("https://open.spotify.com.evil.com/track/abc", P.SPOTIFY),
    ],
)
def test_JNG_01_13_forbidden_link_urls(url: str, platform: Platform) -> None:
    """SEC H1: attacker-controlled hosts must never become shared "Open in" links."""
    assert safe_platform_url(url, platform) is None


def test_safe_url_is_rebuilt_not_echoed() -> None:
    assert (
        safe_platform_url("https://open.spotify.com/track/abc?si=tracking#frag", P.SPOTIFY)
        == "https://open.spotify.com/track/abc"
    )
