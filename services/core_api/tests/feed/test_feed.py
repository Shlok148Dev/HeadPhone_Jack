"""Friends' feed (JNG-05-01, 05-03, 05-06, 05-07; BR-02, BR-06, BR-07)."""

import time

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import ActivityVisibility, PrivacySettings
from accounts.services import create_account
from social import services
from sources.models import Platform, PlatformConnection, SourceStatus
from tests.factories import put_signal

pytestmark = pytest.mark.django_db


def mk(name):
    return create_account(
        email=f"{name}@x.test",
        username=name,
        password="password-1234",
        display_name=name.title(),
        birth_year=1999,
    )


def friends(a, b):
    services.accept(b, services.send_request(a, b))


def client(u):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(u)}")
    return c


@pytest.fixture
def world(fake_redis):
    me, live, recent_new, recent_old, quiet, stranger = (
        mk(n) for n in ("me", "lia", "ron", "oli", "qui", "str")
    )
    for f in (live, recent_new, recent_old, quiet):
        friends(me, f)
    now = time.time()
    put_signal(fake_redis, "np", live.pk, observed_at=now - 10, platform="YOUTUBE_MUSIC")
    put_signal(
        fake_redis,
        "last",
        recent_new.pk,
        observed_at=now - 300,
        platform="APPLE_MUSIC",
        title="Husn",
    )
    put_signal(fake_redis, "last", recent_old.pk, observed_at=now - 7200)
    put_signal(fake_redis, "np", stranger.pk, observed_at=now - 5)
    return {
        "me": me,
        "live": live,
        "ron": recent_new,
        "oli": recent_old,
        "quiet": quiet,
        "stranger": stranger,
    }


def test_JNG_05_01_feed_orders_live_recent_top_hidden(world):
    r = client(world["me"]).get("/api/v1/feed")
    assert r.status_code == 200
    body = r.json()
    names = [c["friend"]["username"] for c in body["results"]]
    assert names == ["lia", "ron", "oli", "qui"]  # BR-02 and newest Recent first
    states = [c["state"] for c in body["results"]]
    assert states == ["LIVE", "RECENT", "RECENT", "HIDDEN"]
    assert body["live_count"] == 1 and body["degraded"] is False
    assert body["results"][0]["freshness_label"] == "Live on YouTube Music"
    assert all("via" not in c for c in body["results"])  # BR-14
    assert "str" not in names  # BR-06: strangers never appear


def test_JNG_05_06_live_filter(world):
    body = client(world["me"]).get("/api/v1/feed", {"filter": "live"}).json()
    assert [c["friend"]["username"] for c in body["results"]] == ["lia"]


def test_blocked_and_private_friends(world):
    services.block(world["me"], world["ron"])  # BR-07
    ps = PrivacySettings.for_user(world["oli"])
    ps.activity_visibility = ActivityVisibility.NOBODY
    ps.save()
    body = client(world["me"]).get("/api/v1/feed").json()
    by = {c["friend"]["username"]: c for c in body["results"]}
    assert "ron" not in by
    assert by["oli"]["state"] == "HIDDEN" and by["oli"]["recording"] is None


def test_JNG_05_07_needs_reconnect_marks_recent_as_delayed(world):
    PlatformConnection.objects.create(
        user=world["ron"], platform=Platform.APPLE_MUSIC, status=SourceStatus.NEEDS_REAUTH
    )
    body = client(world["me"]).get("/api/v1/feed").json()
    ron = next(c for c in body["results"] if c["friend"]["username"] == "ron")
    assert ron["degraded"] is True and ron["state"] == "RECENT" and body["degraded"] is True


def test_JNG_05_04_search_links_for_open_in_my_app(world):
    body = client(world["me"]).get("/api/v1/feed").json()
    ron = next(c for c in body["results"] if c["friend"]["username"] == "ron")
    assert ron["recording"]["search_links"]["SPOTIFY"].startswith(
        "https://open.spotify.com/search/"
    )


def test_single_card_only_for_friends(world):
    c = client(world["me"])
    assert c.get(f"/api/v1/feed/{world['live'].pk}").json()["state"] == "LIVE"
    assert c.get(f"/api/v1/feed/{world['me'].pk}").status_code == 200
    assert c.get(f"/api/v1/feed/{world['stranger'].pk}").status_code == 404


def test_feed_query_count_is_bounded(world, django_assert_max_num_queries):
    c = client(world["me"])
    with django_assert_max_num_queries(60):
        c.get("/api/v1/feed")
