"""Demo world (ADR-0010): personas shared by core-api's seed and ingest-ml's simulator.

Every persona's plays go through the real push endpoint, so the no-false-Live rule and the
honest platform gaps apply exactly as they would for a real user.
"""

import base64
import hashlib
import hmac
from dataclasses import dataclass, field

from .enums import Platform

DEMO_EMAIL = "demo@jingle.local"
DEMO_PASSWORD_DEFAULT = "jingle-demo-2026"  # noqa: S105 - demo-only, documented in README


@dataclass(frozen=True)
class Track:
    artist: str
    title: str
    album: str
    duration_s: int


CATALOG: tuple[Track, ...] = (
    Track("Arijit Singh", "Kesariya", "Brahmastra", 268),
    Track("Arijit Singh", "Tum Hi Ho", "Aashiqui 2", 262),
    Track("Pritam", "Channa Mereya", "Ae Dil Hai Mushkil", 289),
    Track("Prateek Kuhad", "cold/mess", "cold/mess", 301),
    Track("Prateek Kuhad", "Kasoor", "cold/mess", 212),
    Track("AP Dhillon", "Excuses", "Excuses", 176),
    Track("Diljit Dosanjh", "Lover", "MoonChild Era", 187),
    Track("The Local Train", "Choo Lo", "Aalas Ka Pedh", 244),
    Track("Anuv Jain", "Husn", "Husn", 218),
    Track("Kendrick Lamar", "Not Like Us", "GNX", 274),
    Track("Taylor Swift", "Cruel Summer", "Lover", 178),
    Track("The Weeknd", "Blinding Lights", "After Hours", 200),
    Track("Billie Eilish", "Birds of a Feather", "Hit Me Hard and Soft", 210),
    Track("Dua Lipa", "Levitating", "Future Nostalgia", 203),
    Track("Radiohead", "Weird Fishes/Arpeggi", "In Rainbows", 318),
    Track("Frank Ocean", "Pink + White", "Blonde", 184),
    Track("SZA", "Snooze", "SOS", 201),
    Track("Tame Impala", "The Less I Know the Better", "Currents", 216),
    Track("Lucky Ali", "O Sanam", "Sunoh", 305),
    Track("A.R. Rahman", "Kun Faya Kun", "Rockstar", 473),
)

# Host the Companion reports for each web player (music_service in the push payload).
WEB_PLAYER_HOSTS: dict[Platform, str] = {
    Platform.SPOTIFY: "open.spotify.com",
    Platform.APPLE_MUSIC: "music.apple.com",
    Platform.YOUTUBE_MUSIC: "music.youtube.com",
    Platform.AMAZON_MUSIC: "music.amazon.com",
}


@dataclass(frozen=True)
class Persona:
    username: str
    display_name: str
    platform: Platform
    # Share of time spent listening in a browser (Live-capable via the Companion).
    web_share: float
    # Indexes into CATALOG this persona favours.
    favourites: tuple[int, ...]
    college: str = ""
    city: str = "Mumbai"
    tags: tuple[str, ...] = field(default_factory=tuple)


PERSONAS: tuple[Persona, ...] = (
    Persona("demo", "You (demo)", Platform.SPOTIFY, 0.7, (0, 3, 9, 14), "KJ Somaiya"),
    Persona("aanya", "Aanya", Platform.SPOTIFY, 0.8, (0, 1, 2, 8), "KJ Somaiya"),
    Persona("kabir", "Kabir", Platform.SPOTIFY, 0.6, (9, 15, 16, 17), "KJ Somaiya"),
    Persona("meera", "Meera", Platform.APPLE_MUSIC, 0.3, (3, 4, 8, 12)),
    Persona("dev", "Dev", Platform.YOUTUBE_MUSIC, 0.7, (5, 6, 1, 0), "KJ Somaiya"),
    Persona("riya", "Riya", Platform.SPOTIFY, 0.5, (10, 13, 12, 11)),
    Persona("arjun", "Arjun", Platform.AMAZON_MUSIC, 0.4, (18, 19, 2, 1)),
    Persona("zoya", "Zoya", Platform.APPLE_MUSIC, 0.5, (14, 17, 15, 3)),
    Persona("ishaan", "Ishaan", Platform.YOUTUBE_MUSIC, 0.8, (7, 3, 4, 8), "KJ Somaiya"),
    Persona("tara", "Tara", Platform.SPOTIFY, 0.4, (11, 13, 10, 16)),
    Persona("vikram", "Vikram", Platform.AMAZON_MUSIC, 0.0, (19, 18, 1)),  # phone only: never Live
    Persona("sana", "Sana", Platform.YOUTUBE_MUSIC, 0.3, (6, 5, 0, 2)),
    Persona("neel", "Neel", Platform.APPLE_MUSIC, 0.6, (9, 14, 17, 16)),
    # Sprint 5: not the demo login's friends, so it has people to be suggested.
    Persona("kiara", "Kiara", Platform.SPOTIFY, 0.6, (0, 1, 2, 8), "KJ Somaiya"),  # friend of friends
    Persona("rohan", "Rohan", Platform.YOUTUBE_MUSIC, 0.5, (5, 6, 7, 3)),  # friend of friends
    Persona("maya", "Maya", Platform.APPLE_MUSIC, 0.5, (0, 3, 9, 14), city="Pune"),  # taste twin
)


def demo_token(username: str, key: str) -> str:
    """Deterministic scrobble token for a demo persona (``jng_`` + 43 urlsafe chars).

    Derived from SERVICE_TOKEN so the seed (core-api) and the simulator (ingest-ml) agree without
    sharing a file. Only valid while JINGLE_DEMO=1 seeded them.
    """
    digest = hmac.new(key.encode(), f"jingle-demo:{username}".encode(), hashlib.sha256).digest()
    return "jng_" + base64.urlsafe_b64encode(digest).decode().rstrip("=")
