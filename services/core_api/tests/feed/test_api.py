"""GET /api/v1/me/card (JNG-05-01) and GET /api/v1/connections (BR-13, BR-15)."""

import time

import pytest

from sources.models import LinkedSource, PlatformConnection, ScrobbleToken
from tests.factories import put_signal

pytestmark = pytest.mark.django_db

ROUTE_WORDS = (
    "LISTENBRAINZ",
    "LASTFM",
    "COMPANION",
    "DIRECT",
    "EXPORT",
    "via",
    "ListenBrainz",
    "Last.fm",
    "Companion",
)


class TestMyCard:
    def test_own_live_card(self, auth_api, user, fake_redis):
        put_signal(fake_redis, "np", user.pk, observed_at=time.time() - 5, via="LASTFM")
        r = auth_api.get("/api/v1/me/card")
        assert r.status_code == 200
        body = r.json()
        assert body["state"] == "LIVE"
        assert body["friend"]["id"] == str(user.pk)
        assert set(body) == {
            "friend",
            "state",
            "platform",
            "recording",
            "observed_at",
            "freshness_label",
            "degraded",
            "attribution",
        }
        assert "via" not in r.content.decode()
        assert r["Cache-Control"] == "private, no-store"

    def test_unauthenticated(self, api):
        assert api.get("/api/v1/me/card").status_code == 401


class TestConnections:
    def test_lists_platforms_with_honest_capabilities(
        self, auth_api, user, django_assert_max_num_queries
    ):
        PlatformConnection.objects.create(user=user, platform="SPOTIFY", status="CONNECTED")
        PlatformConnection.objects.create(user=user, platform="YOUTUBE_MUSIC", status="CONNECTED")
        PlatformConnection.objects.create(
            user=user, platform="APPLE_MUSIC", status="PENDING_FIRST_PLAY"
        )
        PlatformConnection.objects.create(user=user, platform="AMAZON_MUSIC", status="NEEDS_REAUTH")
        LinkedSource.objects.create(user=user, kind="LISTENBRAINZ")
        ScrobbleToken.objects.create(user=user, token_sha256="b" * 64)
        with django_assert_max_num_queries(8):
            r = auth_api.get("/api/v1/connections")
        assert r.status_code == 200
        rows = {c["platform"]: c for c in r.json()}
        assert rows["SPOTIFY"]["capabilities"] == {
            "live_on_web": True,
            "live_on_phone": True,
            "history": True,
        }
        assert rows["YOUTUBE_MUSIC"]["capabilities"] == {
            "live_on_web": True,
            "live_on_phone": False,
            "history": True,
        }
        assert "isn't shared yet" in rows["YOUTUBE_MUSIC"]["note"]
        assert rows["APPLE_MUSIC"]["capabilities"]["live_on_phone"] is False
        assert rows["AMAZON_MUSIC"]["capabilities"] == {
            "live_on_web": False,
            "live_on_phone": False,
            "history": False,
        }
        text = r.content.decode()
        assert not any(word in text for word in ROUTE_WORDS)

    def test_companion_only_spotify_not_live_on_phone(self, auth_api, user):
        PlatformConnection.objects.create(user=user, platform="SPOTIFY", status="CONNECTED")
        LinkedSource.objects.create(user=user, kind="COMPANION")
        caps = auth_api.get("/api/v1/connections").json()[0]["capabilities"]
        assert caps == {"live_on_web": True, "live_on_phone": False, "history": True}

    def test_no_companion_no_web_live(self, auth_api, user):
        PlatformConnection.objects.create(user=user, platform="APPLE_MUSIC", status="CONNECTED")
        caps = auth_api.get("/api/v1/connections").json()[0]["capabilities"]
        assert caps["live_on_web"] is False and caps["history"] is True

    def test_unknown_platform(self, auth_api, user):
        PlatformConnection.objects.create(user=user, platform="UNKNOWN", status="CONNECTED")
        caps = auth_api.get("/api/v1/connections").json()[0]["capabilities"]
        assert not any(caps.values())

    def test_empty_and_unauthenticated(self, auth_api, api):
        assert auth_api.get("/api/v1/connections").json() == []
        assert api.get("/api/v1/connections").status_code == 401
