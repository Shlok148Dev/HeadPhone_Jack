"""Adapter interface guarantees (Technical Bible 2.1, BR-01)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from jingle_common.enums import Platform, SourceKind, Via
from jingle_common.events import RawTrack

from ingest_ml.adapters.base import (
    COMPANION_ROUTE,
    Capabilities,
    LinkCredential,
    LinkedSource,
    NotSupported,
    NowPlaying,
    PlaylistSpec,
    RawListen,
    SourceAdapter,
    Window,
    assert_live,
)
from ingest_ml.adapters.registry import PUSH_ROUTES, AdapterRegistry

TRACK = RawTrack(artist="Arijit Singh", title="Kesariya")


@dataclass
class FakeExportAdapter:
    """Shape of a non-live source such as a YouTube Takeout import."""

    kind: SourceKind = SourceKind.YOUTUBE_EXPORT
    caps: Capabilities = Capabilities(
        live=False, recent=True, top=True, playlist_write=False, trainable=True
    )

    async def link(self, user_id: UUID, credential: LinkCredential) -> LinkedSource:
        return LinkedSource(user_id=user_id, kind=self.kind)

    async def refresh(self, src: LinkedSource) -> LinkedSource:
        return src

    async def now_playing(self, src: LinkedSource) -> NowPlaying | None:
        return NowPlaying.from_adapter(
            self, via=Via.EXPORT, platform=Platform.YOUTUBE_MUSIC, track=TRACK
        )

    async def recent(self, src: LinkedSource, since: datetime) -> list[RawListen]:
        return []

    async def top(self, src: LinkedSource, window: Window) -> list[RawTrack]:
        return []

    async def write_playlist(self, src: LinkedSource, pl: PlaylistSpec) -> str:
        raise NotSupported("no playlist write")


def test_from_adapter_refuses_non_live() -> None:
    with pytest.raises(NotSupported):
        NowPlaying.from_adapter(
            FakeExportAdapter(), via=Via.EXPORT, platform=Platform.YOUTUBE_MUSIC, track=TRACK
        )
    with pytest.raises(NotSupported):
        assert_live(FakeExportAdapter())


async def test_non_live_adapter_now_playing_raises() -> None:
    a = FakeExportAdapter()
    assert isinstance(a, SourceAdapter)
    src = await a.link(UUID(int=1), LinkCredential(token="secret"))
    with pytest.raises(NotSupported):
        await a.now_playing(src)
    with pytest.raises(NotSupported):
        await a.write_playlist(src, PlaylistSpec(name="x", tracks=[TRACK]))
    assert await a.recent(src, datetime.now(UTC)) == []
    assert await a.top(src, Window.MONTH) == []
    assert await a.refresh(src) is src


def test_now_playing_cannot_be_constructed_directly() -> None:
    with pytest.raises(TypeError):
        NowPlaying(
            kind=SourceKind.COMPANION,
            via=Via.COMPANION,
            platform=Platform.SPOTIFY,
            track=TRACK,
            observed_at=datetime.now(UTC),
        )


def test_companion_route_is_live_and_trainable() -> None:
    caps = COMPANION_ROUTE.caps
    assert (caps.live, caps.recent, caps.top, caps.playlist_write, caps.trainable) == (
        True,
        True,
        False,
        False,
        True,
    )
    assert COMPANION_ROUTE.via is Via.COMPANION
    np = NowPlaying.from_adapter(
        COMPANION_ROUTE, via=Via.COMPANION, platform=Platform.YOUTUBE_MUSIC, track=TRACK
    )
    assert np.kind is SourceKind.COMPANION
    assert np.is_fresh()
    assert not np.is_fresh(np.observed_at + timedelta(seconds=90))
    assert np.is_fresh(np.observed_at + timedelta(seconds=89))
    assert PUSH_ROUTES[SourceKind.COMPANION] is COMPANION_ROUTE


def test_credentials_not_in_repr() -> None:
    assert "secret" not in repr(LinkCredential(token="secret", code="c0de"))


def test_registry_respects_flags() -> None:
    reg = AdapterRegistry()
    reg.register(SourceKind.YOUTUBE_EXPORT, FakeExportAdapter, flag="yt_export_enabled")
    assert reg.load({}) == {}
    assert reg.load({"yt_export_enabled": False}) == {}
    loaded = reg.load({"yt_export_enabled": True})
    assert isinstance(loaded[SourceKind.YOUTUBE_EXPORT], FakeExportAdapter)
    with pytest.raises(ValueError, match="already registered"):
        reg.register(SourceKind.YOUTUBE_EXPORT, FakeExportAdapter)


def test_registry_rejects_mismatched_kind() -> None:
    reg = AdapterRegistry()
    reg.register(SourceKind.LASTFM, FakeExportAdapter)
    with pytest.raises(ValueError, match="built a"):
        reg.load({})
