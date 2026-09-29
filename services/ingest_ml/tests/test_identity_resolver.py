"""Identity resolver v1: ISRC → MBID → norm_key → MusicBrainz fuzzy → unresolved (SRS 4.4)."""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
import respx
from sqlalchemy import select

from ingest_ml.db import artists, now, recordings
from ingest_ml.identity.musicbrainz import MBRecording, MusicBrainzUnavailable, parse_recording
from ingest_ml.identity.normalize import normalise
from ingest_ml.identity.resolver import (
    PENDING_KEY,
    IdentityResolver,
    TrackInput,
    best_match,
    clean_isrc,
)
from ingest_ml.resources import Resources
from ingest_ml.settings import Settings

from .conftest import make_resources

MB_URL = "https://musicbrainz.org/ws/2/recording"
KESARIYA_MBID = "0c3b1a8e-7d0f-4b77-9d2a-0a1e6f1c2b3d"
RELEASE_MBID = "5f1a4c1e-2222-4a3b-8c9d-111122223333"
ARTIST_MBID = "ed3f4831-e3e0-4dc0-9381-f5649e9df221"


def mb_item(
    title: str = "Kesariya",
    artist: str = "Arijit Singh",
    length: int | None = 268000,
    mbid: str = KESARIYA_MBID,
    score: int = 100,
    isrc: str | None = "INZ031412345",
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": mbid,
        "score": score,
        "title": title,
        "length": length,
        "artist-credit": [{"name": artist, "artist": {"id": ARTIST_MBID, "name": artist}}],
        "releases": [{"id": RELEASE_MBID, "title": "Brahmastra"}],
    }
    if isrc:
        item["isrcs"] = [isrc]
    return item


@pytest.fixture
async def mbres() -> AsyncIterator[Resources]:
    cfg = Settings(
        jingle_env="test", musicbrainz_contact="ops@jingle.test", musicbrainz_enabled=True
    )
    r = await make_resources(cfg)
    yield r
    await r.http.aclose()


async def _insert(res: Resources, **values: Any) -> UUID:
    rid = uuid4()
    base = {
        "id": rid,
        "title": "t",
        "artist_name": "a",
        "album": "",
        "artwork_url": "",
        "norm_key": "a|t",
        "resolution": "unresolved",
        "created_at": now(),
        "updated_at": now(),
    }
    async with res.engine.begin() as conn:
        await conn.execute(recordings.insert().values({**base, **values}))
    return rid


async def _row(res: Resources, rid: UUID) -> dict[str, Any]:
    async with res.engine.connect() as conn:
        row = (
            (await conn.execute(select(recordings).where(recordings.c.id == rid))).mappings().one()
        )
    return dict(row)


async def test_isrc_beats_mbid(res: Resources) -> None:
    a = await _insert(res, isrc="USUM71703861", norm_key="x|a")
    mbid = uuid4()
    await _insert(res, mbid=mbid, norm_key="x|b")
    out = await res.resolver.resolve(
        TrackInput("Ed Sheeran", "Perfect", isrc="usum7-1703861", recording_mbid=mbid)
    )
    assert out.recording_id == a


async def test_mbid_match_and_isrc_attached(res: Resources) -> None:
    mbid = uuid4()
    b = await _insert(res, mbid=mbid, norm_key="x|b", resolution="mbid")
    out = await res.resolver.resolve(TrackInput("X", "B", isrc="GBAYE0601498", recording_mbid=mbid))
    assert out.recording_id == b and out.resolution == "mbid"
    assert (await _row(res, b))["isrc"] == "GBAYE0601498"


async def test_new_isrc_upgrades_unresolved_norm_key_row(res: Resources) -> None:
    first = await res.resolver.resolve(TrackInput("Arijit Singh", "Kesariya"))
    assert first.resolution == "unresolved"
    second = await res.resolver.resolve(
        TrackInput(
            "Arijit Singh - Topic",
            "Kesariya (Official Audio)",
            isrc="INZ031412345",
            release_mbid=UUID(RELEASE_MBID),
        )
    )
    assert second.recording_id == first.recording_id
    assert second.resolution == "isrc"
    row = await _row(res, first.recording_id)
    assert row["isrc"] == "INZ031412345"
    assert row["artwork_url"] == f"https://coverartarchive.org/release/{RELEASE_MBID}/front-250"


async def test_conflicting_ids_create_new_row(res: Resources) -> None:
    await _insert(res, isrc="INZ031412345", norm_key="arijit singh|kesariya")
    out = await res.resolver.resolve(TrackInput("Arijit Singh", "Kesariya", isrc="INZ031499999"))
    assert out.resolution == "isrc"
    assert (await _row(res, out.recording_id))["isrc"] == "INZ031499999"


async def test_mbid_only_new_row_with_artwork(res: Resources) -> None:
    out = await res.resolver.resolve(
        TrackInput(
            "Queen", "Bohemian Rhapsody", recording_mbid=uuid4(), release_mbid=UUID(RELEASE_MBID)
        )
    )
    assert out.resolution == "mbid"
    assert out.artwork_url and RELEASE_MBID in out.artwork_url


async def test_norm_key_exact_reuse_and_enrich(res: Resources) -> None:
    a = await res.resolver.resolve(TrackInput("Arijit Singh", 'Kesariya (From "Brahmastra")'))
    b = await res.resolver.resolve(
        TrackInput("ARIJIT SINGH", "kesariya", album="Brahmastra", duration_ms=268000)
    )
    assert a.recording_id == b.recording_id and b.resolution == "unresolved"
    row = await _row(res, a.recording_id)
    assert row["album"] == "Brahmastra" and row["duration_ms"] == 268000
    assert row["title"] == "Kesariya"


async def test_disabled_musicbrainz_makes_no_http_calls(res: Resources) -> None:
    with respx.mock(assert_all_mocked=True) as router:
        out = await res.resolver.resolve(TrackInput("Someone", "Something"))
        assert not router.calls
    assert out.resolution == "unresolved" and not out.pending
    assert await res.redis.llen(PENDING_KEY) == 0


@respx.mock
async def test_fuzzy_match_accepted(mbres: Resources) -> None:
    route = respx.get(MB_URL).mock(
        return_value=httpx.Response(200, json={"recordings": [mb_item()]})
    )
    out = await mbres.resolver.resolve(
        TrackInput("Arijit Singh - Topic", 'Kesariya (From "Brahmastra")', duration_ms=270000)
    )
    assert out.resolution == "fuzzy"
    assert out.artwork_url == f"https://coverartarchive.org/release/{RELEASE_MBID}/front-250"
    req = route.calls.last.request
    assert req.headers["User-Agent"] == "Jingle/0.1 ( ops@jingle.test )"
    assert "fmt=json" in str(req.url)
    row = await _row(mbres, out.recording_id)
    assert str(row["mbid"]) == KESARIYA_MBID and row["isrc"] == "INZ031412345"
    async with mbres.engine.connect() as conn:
        art = (await conn.execute(select(artists))).mappings().one()
    assert str(art["mbid"]) == ARTIST_MBID and row["artist_id"] == art["id"]
    # permanent cache: second lookup of the same song is local
    again = await mbres.resolver.resolve(TrackInput("Arijit Singh", "Kesariya"))
    assert again.recording_id == out.recording_id
    assert route.call_count == 1


@respx.mock
async def test_fuzzy_below_threshold_is_unresolved(mbres: Resources) -> None:
    respx.get(MB_URL).mock(
        return_value=httpx.Response(
            200, json={"recordings": [mb_item(title="Tum Hi Ho"), mb_item(artist="Someone Else")]}
        )
    )
    out = await mbres.resolver.resolve(TrackInput("Arijit Singh", "Kesariya"))
    assert out.resolution == "unresolved" and not out.pending


@respx.mock
async def test_duration_mismatch_rejected(mbres: Resources) -> None:
    respx.get(MB_URL).mock(
        return_value=httpx.Response(200, json={"recordings": [mb_item(length=200000)]})
    )
    out = await mbres.resolver.resolve(TrackInput("Arijit Singh", "Kesariya", duration_ms=268000))
    assert out.resolution == "unresolved"


@respx.mock
async def test_existing_mbid_reused_on_fuzzy(mbres: Resources) -> None:
    existing = await _insert(mbres, mbid=UUID(KESARIYA_MBID), norm_key="other|key")
    respx.get(MB_URL).mock(return_value=httpx.Response(200, json={"recordings": [mb_item()]}))
    out = await mbres.resolver.resolve(TrackInput("Arijit Singh", "Kesariya"))
    assert out.recording_id == existing


@respx.mock
async def test_musicbrainz_error_enqueues(mbres: Resources) -> None:
    respx.get(MB_URL).mock(return_value=httpx.Response(503))
    out = await mbres.resolver.resolve(TrackInput("Arijit Singh", "Kesariya"))
    assert out.resolution == "unresolved" and out.pending
    job = json.loads(await mbres.redis.lpop(PENDING_KEY))
    assert job["recording_id"] == str(out.recording_id) and job["title"] == "Kesariya"


@respx.mock
async def test_musicbrainz_network_error_enqueues(mbres: Resources) -> None:
    respx.get(MB_URL).mock(side_effect=httpx.ConnectError("down"))
    out = await mbres.resolver.resolve(TrackInput("A", "B"))
    assert out.pending


async def test_timebox_keeps_unresolved(res: Resources) -> None:
    class SlowMB:
        async def search_recordings(self, artist: str, title: str) -> list[MBRecording]:
            await asyncio.sleep(5)
            return []

    resolver = IdentityResolver(res.engine, res.redis, SlowMB(), timeout=0.05)  # type: ignore[arg-type]
    out = await resolver.resolve(TrackInput("Arijit Singh", "Kesariya"))
    assert out.resolution == "unresolved" and out.pending
    assert await res.redis.llen(PENDING_KEY) == 1


async def test_import_path_skips_remote_and_enqueues(mbres: Resources) -> None:
    with respx.mock(assert_all_mocked=True) as router:
        out = await mbres.resolver.resolve(TrackInput("A", "B"), allow_remote=False)
        assert not router.calls
    assert out.pending


async def test_musicbrainz_limiter_shared_bucket(mbres: Resources) -> None:
    mb = mbres.resolver._mb
    assert mb is not None
    await mb._acquire()
    with pytest.raises(MusicBrainzUnavailable):
        await mb._acquire(max_wait=0.0)
    assert await mbres.redis.exists("rl:musicbrainz")


def test_best_match_threshold_boundary() -> None:
    norm = normalise("Arijit Singh", "Kesariya")
    exact = parse_recording(mb_item())
    near = parse_recording(mb_item(title="Kesariyaa", mbid=str(uuid4())))
    far = parse_recording(mb_item(title="Kesari", mbid=str(uuid4())))
    assert exact and near and far
    assert best_match(norm, None, [far]) is None
    assert best_match(norm, None, [near]) is near  # 94 ≥ 90
    assert best_match(norm, None, [far, exact]) is exact


def test_parse_recording_tolerates_junk() -> None:
    assert parse_recording({"id": "not-a-uuid", "title": "x"}) is None
    r = parse_recording({"id": KESARIYA_MBID, "title": "x"})
    assert r and r.artist == "" and r.release_mbid is None and r.duration_ms is None


def test_clean_isrc() -> None:
    assert clean_isrc("us-um7-17-03861") == "USUM71703861"
    assert clean_isrc("bogus") is None
    assert clean_isrc(None) is None
