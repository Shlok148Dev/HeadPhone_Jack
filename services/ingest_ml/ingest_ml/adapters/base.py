"""Source adapter interface (Technical Bible 2.1).

Every platform integration implements :class:`SourceAdapter`, declares truthful
:class:`Capabilities`, and raises :class:`NotSupported` for anything it cannot do. A
:class:`NowPlaying` can only be built through :meth:`NowPlaying.from_adapter`, which refuses
non-live adapters, so a false Live state is a code error that tests catch (BR-01).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar, Protocol, runtime_checkable
from uuid import UUID, uuid4

from jingle_common.enums import LIVE_MAX_AGE_SECONDS, Platform, SourceKind, SourceStatus, Via
from jingle_common.events import RawTrack
from pydantic import BaseModel, Field


class NotSupported(Exception):  # noqa: N818 - name fixed by Technical Bible 2.1
    """The source cannot do this (e.g. now-playing on Apple Music)."""


class Capabilities(BaseModel):
    model_config = {"frozen": True}

    live: bool
    recent: bool
    top: bool
    playlist_write: bool
    trainable: bool  # may this data feed models? (SRS BR-04)


class Window(StrEnum):
    WEEK = "WEEK"
    MONTH = "MONTH"
    YEAR = "YEAR"
    ALL_TIME = "ALL_TIME"


class LinkCredential(BaseModel):
    """What the user handed over to link a source. Never logged."""

    token: str | None = Field(default=None, repr=False)
    username: str | None = None
    code: str | None = Field(default=None, repr=False)
    code_verifier: str | None = Field(default=None, repr=False)


class LinkedSource(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    kind: SourceKind
    external_user_id: str = ""
    token_ciphertext: str = Field(default="", repr=False)
    token_key_id: str = ""
    status: SourceStatus = SourceStatus.CONNECTED
    last_ok_at: datetime | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class RawListen(BaseModel):
    track: RawTrack
    played_at: datetime
    platform: Platform = Platform.UNKNOWN
    isrc: str | None = None
    recording_mbid: UUID | None = None
    release_mbid: UUID | None = None


class PlaylistSpec(BaseModel):
    name: str
    description: str = ""
    tracks: list[RawTrack]


class HasCapabilities(Protocol):
    """Anything that can report plays: a full adapter or a push route descriptor."""

    @property
    def kind(self) -> SourceKind: ...

    @property
    def caps(self) -> Capabilities: ...


@runtime_checkable
class SourceAdapter(Protocol):
    kind: SourceKind
    caps: Capabilities

    async def link(self, user_id: UUID, credential: LinkCredential) -> LinkedSource: ...
    async def refresh(self, src: LinkedSource) -> LinkedSource: ...
    async def now_playing(self, src: LinkedSource) -> "NowPlaying | None": ...
    async def recent(self, src: LinkedSource, since: datetime) -> list[RawListen]: ...
    async def top(self, src: LinkedSource, window: Window) -> list[RawTrack]: ...
    async def write_playlist(self, src: LinkedSource, pl: PlaylistSpec) -> str: ...


def assert_live(adapter: HasCapabilities) -> None:
    if not adapter.caps.live:
        raise NotSupported(f"{adapter.kind} cannot report now-playing")


_FACTORY_KEY = object()


@dataclass(frozen=True)
class NowPlaying:
    """A now-playing signal. Build only with :meth:`from_adapter`."""

    kind: SourceKind
    via: Via
    platform: Platform
    track: RawTrack
    observed_at: datetime
    _key: object = field(repr=False, compare=False, default=None)

    def __post_init__(self) -> None:
        if self._key is not _FACTORY_KEY:
            raise TypeError("NowPlaying must be created with NowPlaying.from_adapter()")

    @classmethod
    def from_adapter(
        cls,
        adapter: HasCapabilities,
        *,
        via: Via,
        platform: Platform,
        track: RawTrack,
        observed_at: datetime | None = None,
    ) -> "NowPlaying":
        assert_live(adapter)
        return cls(
            kind=adapter.kind,
            via=via,
            platform=platform,
            track=track,
            observed_at=observed_at or datetime.now(UTC),
            _key=_FACTORY_KEY,
        )

    def is_fresh(self, now: datetime | None = None) -> bool:
        age = ((now or datetime.now(UTC)) - self.observed_at).total_seconds()
        return bool(age < LIVE_MAX_AGE_SECONDS)


@dataclass(frozen=True)
class CompanionRoute:
    """The push route (ADR-0003): Jingle Companion and any scrobbler pointed at /ingest/1/*.

    Not a polling adapter: plays arrive by push, so it only describes capabilities.
    """

    kind: SourceKind = SourceKind.COMPANION
    via: Via = Via.COMPANION
    caps: Capabilities = Capabilities(
        live=True, recent=True, top=False, playlist_write=False, trainable=True
    )
    push_only: ClassVar[bool] = True


COMPANION_ROUTE = CompanionRoute()
