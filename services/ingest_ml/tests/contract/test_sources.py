"""Sprint 2 contract tests: adapters against recorded fixtures, orchestrator routing, poller,
unlink/purge, Takeout import. All offline (respx)."""

import asyncio
import hashlib
import json
import pathlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
import respx
from jingle_common.enums import Platform, SourceKind, SourceStatus
from sqlalchemy import select

from ingest_ml.adapters.base import NotSupported
from ingest_ml.adapters.common import RateLimited, ReauthRequired, request_json
from ingest_ml.adapters.flagged import AppleMusicAdapter
from ingest_ml.adapters.lastfm import api_sig
from ingest_ml.db import platform_connections, recording_links
from ingest_ml.main import create_app
from ingest_ml.orchestrator import POLL_ZSET, ConnectError, Orchestrator
from ingest_ml.poller import poll_due
from ingest_ml.resources import Resources
from ingest_ml.settings import Settings
from ingest_ml.sources_store import get_source, list_sources, save_source
from ingest_ml.takeout import TakeoutError, parse_html, parse_json, sniff_and_parse

from ..conftest import SERVICE_TOKEN, User, create_user, make_resources, track

FIX = pathlib.Path(__file__).parent.parent / "fixtures"
LB = "https://api.listenbrainz.org"
LFM = "https://ws.audioscrobbler.com/2.0/"
SP_API = "https://api.spotify.com/v1"
SP_TOKEN = "https://accounts.spotify.com/api/token"  # noqa: S105
SVC = {"X-Service-Token": SERVICE_TOKEN}


def fx(name: str) -> object:
    return json.loads((FIX / name).read_text(encoding="utf-8"))


@pytest.fixture
async def cres() -> AsyncIterator[Resources]:
    r = await make_resources(
        Settings(
            jingle_env="test",
            service_token=SERVICE_TOKEN,
            lastfm_api_key="k",
            lastfm_shared_secret="s",
            spotify_client_id="cid",
            spotify_redirect_uri="http://127.0.0.1:8080/api/v1/sources/spotify/callback",
        )
    )
    yield r
    await r.http.aclose()
    await r.engine.dispose()


@pytest.fixture
async def u(cres: Resources) -> User:
    user = await create_user(cres.engine)
    await cres.redis.set(f"presence:{user.id}", "1")  # someone has Jingle open: live polling on
    return user


async def _conn_status(res: Resources, user_id: UUID, platform: Platform) -> str | None:
    async with res.engine.connect() as conn:
        row = (
            await conn.execute(
                select(platform_connections.c.status).where(
                    platform_connections.c.user_id == user_id,
                    platform_connections.c.platform == platform.value,
                )
            )
        ).first()
    return row[0] if row else None


# ---- common HTTP behaviour (NFR-AVAIL-04) --------------------------------------------------


async def _nosleep(_: float) -> None:
    return None


@respx.mock
async def test_request_json_retries_5xx_then_succeeds() -> None:
    route = respx.get("https://x.test/a").mock(
        side_effect=[httpx.Response(500), httpx.Response(200, json={"ok": 1})]
    )
    async with httpx.AsyncClient() as http:
        assert await request_json(http, "GET", "https://x.test/a", sleep=_nosleep) == (
            200,
            {"ok": 1},
        )
    assert route.call_count == 2


@respx.mock
async def test_request_json_429_honours_retry_after_then_raises() -> None:
    respx.get("https://x.test/b").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "2"})
    )
    async with httpx.AsyncClient() as http:
        with pytest.raises(RateLimited):
            await request_json(http, "GET", "https://x.test/b", sleep=_nosleep)


@respx.mock
async def test_request_json_401_needs_reauth() -> None:
    respx.get("https://x.test/c").mock(return_value=httpx.Response(401))
    async with httpx.AsyncClient() as http:
        with pytest.raises(ReauthRequired):
            await request_json(http, "GET", "https://x.test/c", sleep=_nosleep)


# ---- ListenBrainz (JNG-01-02) ---------------------------------------------------------------


@respx.mock
async def test_JNG_01_02_valid_listenbrainz_token_links(cres: Resources, u: User) -> None:
    respx.get(f"{LB}/1/validate-token").mock(
        return_value=httpx.Response(200, json=fx("listenbrainz/validate_token_ok.json"))
    )
    await Orchestrator(cres).link_listenbrainz(u.id, Platform.YOUTUBE_MUSIC, "lb-token-123")
    src = await get_source(cres.engine, u.id, SourceKind.LISTENBRAINZ)
    assert src is not None and src.external_user_id == "lb_listener"
    assert "lb-token-123" not in src.token_ciphertext  # sealed (NFR-SEC-01)
    assert src.meta["platform"] == "YOUTUBE_MUSIC"
    assert await _conn_status(cres, u.id, Platform.YOUTUBE_MUSIC) == "PENDING_FIRST_PLAY"
    assert await cres.redis.zscore(POLL_ZSET, str(src.id)) == 0


@respx.mock
async def test_JNG_01_02_invalid_token_exact_copy_and_no_record(cres: Resources, u: User) -> None:
    respx.get(f"{LB}/1/validate-token").mock(
        return_value=httpx.Response(200, json=fx("listenbrainz/validate_token_bad.json"))
    )
    with pytest.raises(ConnectError) as err:
        await Orchestrator(cres).link_listenbrainz(u.id, Platform.SPOTIFY, "nope")
    assert err.value.message == "That token didn't work — copy it again from ListenBrainz settings"
    assert await get_source(cres.engine, u.id, SourceKind.LISTENBRAINZ) is None


@respx.mock
async def test_listenbrainz_poll_live_and_recent(cres: Resources, u: User) -> None:
    respx.get(f"{LB}/1/validate-token").mock(
        return_value=httpx.Response(200, json=fx("listenbrainz/validate_token_ok.json"))
    )
    respx.get(f"{LB}/1/user/lb_listener/playing-now").mock(
        return_value=httpx.Response(200, json=fx("listenbrainz/playing_now.json"))
    )
    respx.get(f"{LB}/1/user/lb_listener/listens").mock(
        return_value=httpx.Response(200, json=fx("listenbrainz/listens.json"))
    )
    orch = Orchestrator(cres)
    await orch.link_listenbrainz(u.id, Platform.YOUTUBE_MUSIC, "lb-token-123")
    counts = await poll_due(orch, {})
    assert counts["live"] == 1 and counts["listens"] == 2
    np = await cres.redis.hgetall(f"np:{u.id}")
    assert (
        np["platform"] == "SPOTIFY" and np["via"] == "LISTENBRAINZ"
    )  # platform = the player, not the route
    docs = await cres.mongo["listens"].find({}).to_list(None)
    assert {d["meta"]["platform"] for d in docs} == {
        "YOUTUBE_MUSIC"
    }  # fallback to the connected platform
    assert all(d["trainable"] for d in docs)  # ListenBrainz data may train models (BR-04)
    assert await _conn_status(cres, u.id, Platform.YOUTUBE_MUSIC) == "CONNECTED"


# ---- Last.fm (JNG-01-05) --------------------------------------------------------------------


def test_lastfm_api_sig_matches_spec() -> None:
    params = {"api_key": "k", "method": "auth.getSession", "token": "t", "format": "json"}
    assert api_sig(params, "s") == hashlib.md5(b"api_keykmethodauth.getSessiontokents").hexdigest()  # noqa: S324


@respx.mock
async def test_JNG_01_05_spotify_via_lastfm_is_live_and_not_trainable(
    cres: Resources, u: User
) -> None:
    orch = Orchestrator(cres)
    plan = await orch.start(u.id, Platform.SPOTIFY, allowlisted=False, flags={})
    assert plan.action == "lastfm_then_spotify" and plan.url and "last.fm/api/auth" in plan.url
    state = plan.url.split("state%3D")[1]
    respx.get(LFM, params={"method": "auth.getSession"}).mock(
        return_value=httpx.Response(200, json=fx("lastfm/get_session.json"))
    )
    respx.get(LFM, params={"method": "user.getRecentTracks", "limit": "1"}).mock(
        return_value=httpx.Response(200, json=fx("lastfm/recent_nowplaying.json"))
    )
    respx.get(LFM, params={"method": "user.getRecentTracks", "limit": "200"}).mock(
        return_value=httpx.Response(200, json=fx("lastfm/recent_history.json"))
    )
    user_id, platform = await orch.complete_lastfm(state, "cb-token")
    assert user_id == u.id and platform is Platform.SPOTIFY
    counts = await poll_due(orch, {})
    assert counts["live"] == 1 and counts["listens"] == 2
    np = await cres.redis.hgetall(f"np:{u.id}")
    assert np["platform"] == "SPOTIFY" and np["via"] == "LASTFM"
    docs = await cres.mongo["listens"].find({}).to_list(None)
    assert docs and not any(d["trainable"] for d in docs)  # Last.fm never trains (BR-04)


@respx.mock
async def test_lastfm_private_profile_needs_reconnect(cres: Resources, u: User) -> None:
    respx.get(LFM, params={"method": "user.getInfo"}).mock(
        return_value=httpx.Response(200, json=fx("lastfm/user_info.json"))
    )
    orch = Orchestrator(cres)
    await orch.link_lastfm_username(u.id, Platform.SPOTIFY, "lfm_listener")
    respx.get(LFM, params={"method": "user.getRecentTracks"}).mock(
        return_value=httpx.Response(200, json=fx("lastfm/error_private.json"))
    )
    counts = await poll_due(orch, {})
    assert counts["reauth"] == 1
    src = await get_source(cres.engine, u.id, SourceKind.LASTFM)
    assert (
        src and src.status is SourceStatus.NEEDS_REAUTH and src.meta["reason"] == "private_profile"
    )
    assert await _conn_status(cres, u.id, Platform.SPOTIFY) == "NEEDS_REAUTH"  # JNG-01-11


@respx.mock
async def test_lastfm_rate_limit_skips_and_reschedules(cres: Resources, u: User) -> None:
    respx.get(LFM, params={"method": "user.getInfo"}).mock(
        return_value=httpx.Response(200, json=fx("lastfm/user_info.json"))
    )
    orch = Orchestrator(cres)
    await orch.link_lastfm_username(u.id, Platform.SPOTIFY, "lfm_listener")
    respx.get(LFM, params={"method": "user.getRecentTracks"}).mock(
        return_value=httpx.Response(200, json=fx("lastfm/error_rate_limit.json"))
    )
    counts = await poll_due(orch, {})
    assert counts["skipped"] == 1
    src = await get_source(cres.engine, u.id, SourceKind.LASTFM)
    assert src and src.status is not SourceStatus.NEEDS_REAUTH
    assert (await cres.redis.zscore(POLL_ZSET, str(src.id)) or 0) > datetime.now(UTC).timestamp()


# ---- Direct Spotify (JNG-01-04) ----------------------------------------------------------------


async def test_JNG_01_04_route_choice(cres: Resources, res: Resources, u: User) -> None:
    plan = await Orchestrator(cres).start(u.id, Platform.SPOTIFY, allowlisted=True, flags={})
    assert (
        plan.action == "redirect"
        and plan.url
        and plan.url.startswith("https://accounts.spotify.com/authorize?")
    )
    assert "code_challenge_method=S256" in plan.url
    # Non-allowlisted member gets the bridge path instead of an OAuth button (SRS JNG-01-04).
    assert (
        await Orchestrator(cres).start(u.id, Platform.SPOTIFY, allowlisted=False, flags={})
    ).action == "lastfm_then_spotify"
    # Nothing configured (no keys): browser only, never an error (BR-15).
    other = await create_user(res.engine)
    assert (
        await Orchestrator(res).start(other.id, Platform.SPOTIFY, allowlisted=True, flags={})
    ).action == "browser"
    assert (
        await Orchestrator(cres).start(u.id, Platform.APPLE_MUSIC, allowlisted=True, flags={})
    ).action == "browser"


async def test_JNG_01_04_allowlist_full_falls_back(cres: Resources) -> None:
    from ingest_ml.adapters.base import LinkedSource

    for _ in range(5):
        other = await create_user(cres.engine)
        await save_source(cres.engine, LinkedSource(user_id=other.id, kind=SourceKind.SPOTIFY))
    newcomer = await create_user(cres.engine)
    plan = await Orchestrator(cres).start(newcomer.id, Platform.SPOTIFY, allowlisted=True, flags={})
    assert plan.action == "lastfm_then_spotify"


async def _link_spotify(cres: Resources, u: User) -> Orchestrator:
    orch = Orchestrator(cres)
    plan = await orch.start(u.id, Platform.SPOTIFY, allowlisted=True, flags={})
    assert plan.url
    state = plan.url.split("state=")[1].split("&")[0]
    respx.post(SP_TOKEN).mock(return_value=httpx.Response(200, json=fx("spotify/token.json")))
    respx.get(f"{SP_API}/me").mock(return_value=httpx.Response(200, json=fx("spotify/me.json")))
    await orch.complete_spotify(state, "auth-code")
    return orch


@respx.mock
async def test_spotify_direct_is_display_only(cres: Resources, u: User) -> None:
    orch = await _link_spotify(cres, u)
    respx.get(f"{SP_API}/me/player/currently-playing").mock(
        return_value=httpx.Response(200, json=fx("spotify/currently_playing.json"))
    )
    respx.get(f"{SP_API}/me/player/recently-played").mock(
        return_value=httpx.Response(200, json=fx("spotify/recently_played.json"))
    )
    counts = await poll_due(orch, {})
    assert counts["live"] == 1 and counts["listens"] == 1  # the podcast episode is skipped
    np = await cres.redis.hgetall(f"np:{u.id}")
    event = json.loads(np["event"])
    assert np["via"] == "DIRECT" and event["artwork_url"].startswith("https://i.scdn.co/")
    doc = await cres.mongo["listens"].find_one({})
    assert (
        doc and doc["trainable"] is False and doc["analytics_allowed"] is False
    )  # BR-03, ADR-0013
    async with cres.engine.connect() as conn:
        assert (
            await conn.execute(select(recording_links))
        ).all() == []  # nothing in the shared catalog


@respx.mock
async def test_spotify_not_on_allowlist_falls_back(cres: Resources, u: User) -> None:
    orch = Orchestrator(cres)
    plan = await orch.start(u.id, Platform.SPOTIFY, allowlisted=True, flags={})
    assert plan.url
    state = plan.url.split("state=")[1].split("&")[0]
    respx.post(SP_TOKEN).mock(return_value=httpx.Response(200, json=fx("spotify/token.json")))
    respx.get(f"{SP_API}/me").mock(return_value=httpx.Response(403))
    with pytest.raises(ConnectError) as err:
        await orch.complete_spotify(state, "auth-code")
    assert err.value.code == "SPOTIFY_NOT_AVAILABLE"
    assert await get_source(cres.engine, u.id, SourceKind.SPOTIFY) is None


async def test_oauth_state_is_single_use(cres: Resources, u: User) -> None:
    orch = Orchestrator(cres)
    plan = await orch.start(u.id, Platform.SPOTIFY, allowlisted=True, flags={})
    assert plan.url
    state = plan.url.split("state=")[1].split("&")[0]
    with respx.mock:
        respx.post(SP_TOKEN).mock(return_value=httpx.Response(200, json=fx("spotify/token.json")))
        respx.get(f"{SP_API}/me").mock(return_value=httpx.Response(200, json=fx("spotify/me.json")))
        await orch.complete_spotify(state, "c")
    with pytest.raises(ConnectError):
        await orch.complete_spotify(state, "c")


@respx.mock
async def test_JNG_01_09_unlink_spotify_purges_direct_data_and_keeps_disabled(
    cres: Resources, u: User
) -> None:
    orch = await _link_spotify(cres, u)
    respx.get(f"{SP_API}/me/player/currently-playing").mock(
        return_value=httpx.Response(200, json=fx("spotify/currently_playing.json"))
    )
    respx.get(f"{SP_API}/me/player/recently-played").mock(
        return_value=httpx.Response(200, json=fx("spotify/recently_played.json"))
    )
    await poll_due(orch, {})
    await orch.unlink(u.id, Platform.SPOTIFY)
    assert await get_source(cres.engine, u.id, SourceKind.SPOTIFY) is None
    assert await cres.mongo["listens"].count_documents({"meta.via": "DIRECT"}) == 0
    assert not await cres.redis.exists(f"np:{u.id}")
    assert await cres.redis.xrange("events:listen") == []
    assert await _conn_status(cres, u.id, Platform.SPOTIFY) == "DISABLED"
    # A Companion push for the same platform does not silently re-enable it.
    app = create_app(resources=cres)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://i") as c:
        r = await c.post(
            "/ingest/1/submit-listens",
            headers=u.auth,
            json={
                "listen_type": "playing_now",
                "payload": [{"track_metadata": track(music_service="open.spotify.com")}],
            },
        )
        assert r.status_code == 200
    assert await _conn_status(cres, u.id, Platform.SPOTIFY) == "DISABLED"


@respx.mock
async def test_spotify_token_refresh_when_expired(cres: Resources, u: User) -> None:
    from ingest_ml.adapters.common import seal

    orch = await _link_spotify(cres, u)
    src = await get_source(cres.engine, u.id, SourceKind.SPOTIFY)
    assert src and cres.cipher
    src.token_ciphertext = seal(
        cres.cipher, {"access_token": "old", "refresh_token": "r", "expires_at": 0}, u.id
    )
    await save_source(cres.engine, src)
    refreshed = await orch.spotify.refresh(src)
    assert refreshed.token_ciphertext != src.token_ciphertext


# ---- Flagged adapters (ADR-0001, BR-11) --------------------------------------------------------


async def test_flagged_adapters_absent_while_flag_off(cres: Resources) -> None:
    orch = Orchestrator(cres)
    for kind in (SourceKind.APPLE_MUSIC, SourceKind.AMAZON_MUSIC, SourceKind.YOUTUBE_EXPORT):
        assert orch.adapter(kind, {}) is None


@respx.mock
async def test_apple_music_recent_is_estimated_and_never_live(cres: Resources, u: User) -> None:
    from ingest_ml.adapters.base import LinkCredential

    assert cres.cipher
    apple = AppleMusicAdapter(cres.http, cres.cipher, cres.source_buckets["apple"], "dev-jwt")
    src = await apple.link(u.id, LinkCredential(token="music-user-token"))
    respx.get("https://api.music.apple.com/v1/me/recent/played/tracks").mock(
        return_value=httpx.Response(200, json=fx("apple/recent_played.json"))
    )
    plays = await apple.recent_plays(src, datetime.now(UTC))
    assert len(plays) == 2 and all(p.played_at_estimated for p in plays)
    assert (
        plays[0].isrc == "INZ031900123"
        and plays[0].artwork_url
        and "{w}" not in plays[0].artwork_url
    )
    assert await apple.recent_plays(src, datetime.now(UTC)) == []  # seen items aren't re-recorded
    with pytest.raises(NotSupported):
        await apple.now_playing(src)


# ---- YouTube Takeout (JNG-01-06, ADR-0015) --------------------------------------------------


def test_takeout_json_keeps_music_only_and_cleans_titles() -> None:
    with open(FIX / "takeout/watch-history.json", "rb") as fp:
        entries = list(parse_json(fp))
    assert [(e.artist, e.title) for e in entries] == [
        ("Arijit Singh", 'Kesariya (From "Brahmastra")'),
        ("AP Dhillon", "Excuses"),
    ]


def test_takeout_html_parses_ist_times() -> None:
    entries = list(parse_html((FIX / "takeout/watch-history.html").read_bytes()))
    assert len(entries) == 1
    assert entries[0].artist == "Arijit Singh" and entries[0].title == "Kesariya"
    assert entries[0].time == datetime(2026, 9, 28, 15, 44, 3, tzinfo=UTC)


def test_takeout_rejects_other_files(tmp_path: pathlib.Path) -> None:
    p = tmp_path / "x.upload"
    p.write_text("hello")
    with pytest.raises(TakeoutError):
        sniff_and_parse(str(p))


async def test_JNG_01_06_import_endpoint(
    client: httpx.AsyncClient, res: Resources, user: User
) -> None:
    data = (FIX / "takeout/watch-history.json").read_bytes()
    r = await client.post(
        "/internal/imports/youtube",
        headers=SVC,
        data={"user_id": str(user.id)},
        files={"file": ("watch-history.json", data, "application/json")},
    )
    assert r.status_code == 202
    job = r.json()["job_id"]
    for _ in range(50):
        await asyncio.sleep(0.05)
        st = (
            await client.get(
                f"/internal/imports/{job}", headers=SVC, params={"user_id": str(user.id)}
            )
        ).json()
        if st["status"] in ("done", "failed"):
            break
    assert st == {"status": "done", "imported": 2, "found": 2}
    docs = await res.mongo["listens"].find({}).to_list(None)
    assert {d["meta"]["via"] for d in docs} == {"EXPORT"}
    assert not await res.redis.exists(f"np:{user.id}")  # exports are never Live (BR-01)
    assert await _conn_status(res, user.id, Platform.YOUTUBE_MUSIC) == "CONNECTED"
    other = await client.get(
        f"/internal/imports/{job}", headers=SVC, params={"user_id": str(UUID(int=1))}
    )
    assert other.status_code == 404  # jobs are private to their user


async def test_import_rejects_non_takeout(client: httpx.AsyncClient, user: User) -> None:
    r = await client.post(
        "/internal/imports/youtube",
        headers=SVC,
        data={"user_id": str(user.id)},
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    job = r.json()["job_id"]
    for _ in range(50):
        await asyncio.sleep(0.05)
        st = (
            await client.get(
                f"/internal/imports/{job}", headers=SVC, params={"user_id": str(user.id)}
            )
        ).json()
        if st["status"] in ("done", "failed"):
            break
    assert st["status"] == "failed" and "Takeout" in st["error"]


# ---- Internal API wiring --------------------------------------------------------------------


async def test_connect_api_requires_service_token(client: httpx.AsyncClient, user: User) -> None:
    body = {"user_id": str(user.id), "platform": "SPOTIFY"}
    assert (await client.post("/internal/connect/start", json=body)).status_code == 401
    r = await client.post("/internal/connect/start", json=body, headers=SVC)
    assert r.status_code == 200 and r.json()["action"] == "browser"
    r = await client.post("/internal/poll/due", json={}, headers=SVC)
    assert r.status_code == 200 and r.json()["polled"] == 0
    assert (
        await list_sources(client._transport.app.state.resources.engine, [SourceKind.SPOTIFY]) == []
    )  # type: ignore[attr-defined]


@respx.mock
async def test_adaptive_polling_skips_live_when_nobody_watches(cres: Resources) -> None:
    idle = await create_user(cres.engine)  # no presence:/watched: keys
    respx.get(f"{LB}/1/validate-token").mock(
        return_value=httpx.Response(200, json=fx("listenbrainz/validate_token_ok.json"))
    )
    now_route = respx.get(f"{LB}/1/user/lb_listener/playing-now").mock(
        return_value=httpx.Response(200, json=fx("listenbrainz/playing_now.json"))
    )
    respx.get(f"{LB}/1/user/lb_listener/listens").mock(
        return_value=httpx.Response(200, json=fx("listenbrainz/listens.json"))
    )
    orch = Orchestrator(cres)
    await orch.link_listenbrainz(idle.id, Platform.SPOTIFY, "tok")
    counts = await poll_due(orch, {})
    assert counts["live"] == 0 and counts["listens"] == 2 and not now_route.called
    await cres.redis.set(f"watched:{idle.id}", "1")  # a friend opened Jingle
    await cres.redis.zadd(
        POLL_ZSET, {str((await get_source(cres.engine, idle.id, SourceKind.LISTENBRAINZ)).id): 0}
    )  # type: ignore[union-attr]
    assert (await poll_due(orch, {}))["live"] == 1
