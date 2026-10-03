"""Jingle Connect endpoints: consent gates, allowlist, callbacks, unlink, imports (JNG-01-02…09)."""

import json

import httpx
import pytest
import respx
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import ConsentPurpose
from accounts.services import give_consent, withdraw_consent

pytestmark = pytest.mark.django_db
INGEST = "http://ingest-ml.test:8001"


@pytest.fixture
def ingest(settings):
    settings.INGEST_INTERNAL_URL = INGEST
    settings.SERVICE_TOKEN = "svc-token"
    settings.PUBLIC_BASE_URL = "http://127.0.0.1:8080"
    with respx.mock(base_url=INGEST, assert_all_called=False) as mock:
        yield mock


@pytest.fixture
def sharing(user):
    give_consent(user, ConsentPurpose.ACTIVITY_SHARING)


def test_connect_requires_activity_sharing(auth_api, ingest):
    route = ingest.post("/internal/connect/start")
    r = auth_api.post("/api/v1/sources/spotify/connect")
    assert r.status_code == 409 and r.json()["error"]["code"] == "CONSENT_REQUIRED"
    assert not route.called


def test_JNG_01_14_connect_passes_allowlist_and_flags(auth_api, user, ingest, sharing, settings):
    settings.SPOTIFY_ALLOWLIST = f" other@x.com , {user.email.upper()} "
    route = ingest.post("/internal/connect/start").mock(
        return_value=httpx.Response(
            200,
            json={
                "action": "redirect",
                "url": "https://accounts.spotify.com/authorize?x",
                "live_on_phone": True,
            },
        )
    )
    r = auth_api.post("/api/v1/sources/SPOTIFY/connect")
    assert r.status_code == 200 and r.json()["action"] == "redirect"
    sent = json.loads(route.calls.last.request.content)
    assert sent["allowlisted"] is True and sent["platform"] == "SPOTIFY"
    assert sent["flags"]["amazon_music_enabled"] is False  # BR-11
    assert route.calls.last.request.headers["X-Service-Token"] == "svc-token"


def test_lastfm_route_needs_its_own_consent(auth_api, user, ingest, sharing):
    ingest.post("/internal/connect/start").mock(
        return_value=httpx.Response(
            200,
            json={
                "action": "lastfm_then_spotify",
                "url": "https://www.last.fm/api/auth/?x",
                "live_on_phone": True,
            },
        )
    )
    r = auth_api.post("/api/v1/sources/spotify/connect")
    assert r.status_code == 409 and r.json()["error"]["details"]["purpose"] == "lastfm_link"
    give_consent(user, ConsentPurpose.LASTFM_LINK)
    assert (
        auth_api.post("/api/v1/sources/spotify/connect").json()["action"] == "lastfm_then_spotify"
    )


def test_unknown_platform_404(auth_api, ingest, sharing):
    assert auth_api.post("/api/v1/sources/tidal/connect").status_code == 404


def test_spotify_callback_redirects_back_to_settings(api, ingest):
    ingest.post("/internal/connect/spotify/callback").mock(
        return_value=httpx.Response(200, json={"user_id": "u", "platform": "SPOTIFY"})
    )
    r = api.get("/api/v1/sources/spotify/callback", {"state": "s", "code": "c"})
    assert r.status_code == 302
    assert r["Location"] == "http://127.0.0.1:8080/settings/connections?connected=SPOTIFY"


def test_spotify_callback_fallback_is_quiet(api, ingest):
    ingest.post("/internal/connect/spotify/callback").mock(
        return_value=httpx.Response(
            400, json={"error": {"code": "SPOTIFY_NOT_AVAILABLE", "message": "m"}}
        )
    )
    r = api.get("/api/v1/sources/spotify/callback", {"state": "s", "code": "c"})
    assert r["Location"].endswith("error=spotify_not_available&platform=SPOTIFY")
    assert api.get("/api/v1/sources/spotify/callback", {"error": "access_denied"})[
        "Location"
    ].endswith("error=cancelled&platform=SPOTIFY")


def test_spotify_refused_continues_into_lastfm(api, ingest, user):
    from accounts.services import active_consent
    url = "https://www.last.fm/api/auth/?api_key=k&cb=x"
    ingest.post("/internal/connect/spotify/callback").mock(
        return_value=httpx.Response(
            200, json={"user_id": str(user.pk), "platform": "SPOTIFY", "next": url}
        )
    )
    r = api.get("/api/v1/sources/spotify/callback", {"state": "s", "code": "c"})
    assert r.status_code == 302 and r["Location"] == url
    assert active_consent(user, ConsentPurpose.LASTFM_LINK) is not None
    # Never an open redirect: anything but Last.fm's auth page goes back to the app.
    ingest.post("/internal/connect/spotify/callback").mock(
        return_value=httpx.Response(
            200, json={"user_id": str(user.pk), "platform": "SPOTIFY", "next": "https://evil.test"}
        )
    )
    r = api.get("/api/v1/sources/spotify/callback", {"state": "s", "code": "c"})
    assert r["Location"].endswith("connected=SPOTIFY")


def test_lastfm_callback(api, ingest):
    ingest.post("/internal/connect/lastfm/callback").mock(
        return_value=httpx.Response(200, json={"user_id": "u", "platform": "SPOTIFY"})
    )
    r = api.get("/api/v1/sources/lastfm/callback", {"state": "s", "token": "t"})
    assert "connected=SPOTIFY" in r["Location"] and "then=link_spotify_lastfm" in r["Location"]


def test_JNG_01_02_listenbrainz_invalid_token_copy(auth_api, ingest, sharing):
    msg = "That token didn't work — copy it again from ListenBrainz settings"
    ingest.post("/internal/connect/listenbrainz").mock(
        return_value=httpx.Response(400, json={"error": {"code": "TOKEN_INVALID", "message": msg}})
    )
    r = auth_api.post(
        "/api/v1/sources/listenbrainz", {"platform": "YOUTUBE_MUSIC", "token": "bad"}, format="json"
    )
    assert r.status_code == 400 and r.json()["error"]["message"] == msg


def test_listenbrainz_link_ok(auth_api, ingest, sharing):
    ingest.post("/internal/connect/listenbrainz").mock(
        return_value=httpx.Response(201, json={"linked": True})
    )
    r = auth_api.post(
        "/api/v1/sources/listenbrainz", {"platform": "SPOTIFY", "token": "good"}, format="json"
    )
    assert r.status_code == 201


def test_lastfm_username_needs_consent(auth_api, user, ingest, sharing):
    r = auth_api.post(
        "/api/v1/sources/lastfm/username", {"platform": "SPOTIFY", "username": "x"}, format="json"
    )
    assert r.status_code == 409
    give_consent(user, ConsentPurpose.LASTFM_LINK)
    ingest.post("/internal/connect/lastfm/username").mock(
        return_value=httpx.Response(201, json={"linked": True})
    )
    assert (
        auth_api.post(
            "/api/v1/sources/lastfm/username",
            {"platform": "SPOTIFY", "username": "x"},
            format="json",
        ).status_code
        == 201
    )


def test_JNG_01_09_unlink(auth_api, user, ingest):
    route = ingest.delete(f"/internal/connections/{user.pk}/APPLE_MUSIC").mock(
        return_value=httpx.Response(204)
    )
    assert auth_api.delete("/api/v1/connections/apple_music").status_code == 204
    assert route.called


@pytest.mark.django_db(transaction=True)
def test_withdrawing_lastfm_consent_removes_route(user, ingest):
    route = ingest.delete(f"/internal/sources/{user.pk}/LASTFM").mock(
        return_value=httpx.Response(204)
    )
    give_consent(user, ConsentPurpose.LASTFM_LINK)
    withdraw_consent(user, ConsentPurpose.LASTFM_LINK)
    assert route.called


def test_JNG_01_06_youtube_import(auth_api, ingest, sharing):
    ingest.post("/internal/imports/youtube").mock(
        return_value=httpx.Response(202, json={"job_id": "j1", "status": "queued"})
    )
    ingest.get("/internal/imports/j1").mock(
        return_value=httpx.Response(200, json={"status": "done", "imported": 2})
    )
    f = SimpleUploadedFile("watch-history.json", b"[]", content_type="application/json")
    r = auth_api.post("/api/v1/imports/youtube", {"file": f}, format="multipart")
    assert r.status_code == 202 and r.json()["job_id"] == "j1"
    assert auth_api.get("/api/v1/imports/j1").json() == {"status": "done", "imported": 2}


def test_import_requires_a_file(auth_api, ingest, sharing):
    r = auth_api.post("/api/v1/imports/youtube", {}, format="multipart")
    assert r.status_code == 400


def test_upstream_down_is_502(auth_api, ingest, sharing):
    ingest.post("/internal/connect/start").mock(side_effect=httpx.ConnectError("down"))
    r = auth_api.post("/api/v1/sources/spotify/connect")
    assert r.status_code == 502 and r.json()["error"]["code"] == "UPSTREAM_UNAVAILABLE"


def test_poll_task_sends_flags(ingest, settings):
    from sources.tasks import drain_identity_queue, poll_sources

    route = ingest.post("/internal/poll/due").mock(
        return_value=httpx.Response(200, json={"polled": 0})
    )
    ingest.post("/internal/identity/drain?limit=40").mock(
        return_value=httpx.Response(200, json={"processed": 0})
    )
    assert poll_sources() == {"polled": 0}
    assert "apple_music_enabled" in json.loads(route.calls.last.request.content)["flags"]
    assert drain_identity_queue() == {"processed": 0}
    ingest.post("/internal/poll/due").mock(side_effect=httpx.ConnectError("down"))
    assert poll_sources() == {}


# ---- One-click connect (D-CONNECT-01): pressing Connect is the consent --------------------------


def test_one_click_connect_records_consent_and_lastfm_route(auth_api, user, ingest):
    from accounts.services import active_consent

    ingest.post("/internal/connect/start").mock(
        return_value=httpx.Response(
            200,
            json={
                "action": "lastfm_then_spotify",
                "url": "https://www.last.fm/api/auth/?x",
                "live_on_phone": True,
            },
        )
    )
    # Without the button's consent it still refuses (nothing is shared silently)…
    assert auth_api.post("/api/v1/sources/spotify/connect").status_code == 409
    # …with it, both purposes are recorded itemised and the Last.fm plan comes straight back.
    r = auth_api.post("/api/v1/sources/spotify/connect", {"consent": True}, format="json")
    assert r.status_code == 200 and r.json()["action"] == "lastfm_then_spotify"
    assert active_consent(user, ConsentPurpose.ACTIVITY_SHARING) is not None
    assert active_consent(user, ConsentPurpose.LASTFM_LINK) is not None


def test_apple_login_link_forwards_token_never_echoes(auth_api, user, ingest, sharing):
    route = ingest.post("/internal/connect/apple").mock(
        return_value=httpx.Response(201, json={"linked": True})
    )
    mut = "mut-" + "z" * 60
    r = auth_api.post("/api/v1/sources/apple/link", {"music_user_token": mut}, format="json")
    assert r.status_code == 201 and mut not in r.content.decode()
    sent = json.loads(route.calls.last.request.content)
    assert sent["music_user_token"] == mut and sent["user_id"] == str(user.pk)
    assert (
        auth_api.post(
            "/api/v1/sources/apple/link", {"music_user_token": "short"}, format="json"
        ).status_code
        == 400
    )


def test_apple_link_needs_sharing_consent(auth_api, ingest):
    r = auth_api.post("/api/v1/sources/apple/link", {"music_user_token": "m" * 40}, format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "CONSENT_REQUIRED"
