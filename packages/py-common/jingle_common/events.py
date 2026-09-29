"""Normalised listening event (Technical Bible 2.4, CONTRACTS.md §5)."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .enums import EventKind, Platform, Via


class RawTrack(BaseModel):
    artist: str
    title: str
    album: str | None = None
    duration_ms: int | None = None


class ListenEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    recording_id: UUID | None = None
    raw: RawTrack
    artwork_url: str | None = None
    platform: Platform = Platform.UNKNOWN
    via: Via
    kind: EventKind
    played_at: datetime
    observed_at: datetime
    trainable: bool = True
    analytics_allowed: bool = True
    played_at_estimated: bool = False


def permitted_for_training(event: ListenEvent) -> bool:
    """BR-03/BR-04: direct-Spotify API data and Last.fm data never train models."""
    if event.via is Via.LASTFM:
        return False
    if event.via is Via.DIRECT and event.platform is Platform.SPOTIFY:
        return False
    return event.trainable


def default_trainable(via: Via, platform: Platform) -> bool:
    """The trainable flag an event gets at ingestion time."""
    if via is Via.LASTFM:
        return False
    return not (via is Via.DIRECT and platform is Platform.SPOTIFY)


def _is_direct_spotify(via: Via, platform: Platform) -> bool:
    return via is Via.DIRECT and platform is Platform.SPOTIFY


def default_analytics_allowed(via: Via, platform: Platform) -> bool:
    """Spotify Policy III.13 (ADR-0013): direct-Spotify data never feeds stats, scores or profiles."""
    return not _is_direct_spotify(via, platform)


def permitted_for_analytics(event: ListenEvent) -> bool:
    """Gate for stats, compatibility, timeline, recaps, battles, Blends and suggestions."""
    return event.analytics_allowed and not _is_direct_spotify(event.via, event.platform)
