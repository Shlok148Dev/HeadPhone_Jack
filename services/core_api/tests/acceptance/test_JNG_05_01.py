"""JNG-05-01 No false Live (BR-01). Steps drive GET /api/v1/me/card with time frozen."""

import json

import pytest
import time_machine
from pytest_bdd import given, parsers, scenarios, then, when
from rest_framework.test import APIClient

from sources.models import LinkedSource, PlatformConnection
from tests.factories import UserFactory, put_signal

pytestmark = pytest.mark.django_db

scenarios("../features/ep05/JNG-05-01_no_false_live.feature")

NOW = "2026-09-29T10:15:00Z"
NOW_TS = 1790676900.0  # 2026-09-29T10:15:00Z


@pytest.fixture
def kabir(db):
    return UserFactory(username="kabir", display_name="Kabir")


def _has_key(obj, key):
    if isinstance(obj, dict):
        return key in obj or any(_has_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_key(v, key) for v in obj)
    return False


@given("Kabir has only Apple Music linked")
def apple_only(kabir, fake_redis):
    PlatformConnection.objects.create(user=kabir, platform="APPLE_MUSIC", status="CONNECTED")
    LinkedSource.objects.create(user=kabir, kind="APPLE_MUSIC")
    # Even a brand-new Apple Music play (direct API) must not produce Live.
    put_signal(fake_redis, "np", kabir.pk, observed_at=NOW_TS - 5, via="DIRECT",
               platform="APPLE_MUSIC")
    put_signal(fake_redis, "last", kabir.pk, observed_at=NOW_TS - 5, via="DIRECT",
               platform="APPLE_MUSIC")


@given("Kabir's last ListenBrainz playing-now signal is 120 seconds old")
def stale_np(kabir, fake_redis):
    put_signal(fake_redis, "np", kabir.pk, observed_at=NOW_TS - 120, via="LISTENBRAINZ",
               platform="SPOTIFY")
    put_signal(fake_redis, "last", kabir.pk, observed_at=NOW_TS - 120, via="LISTENBRAINZ",
               platform="SPOTIFY")


@given("Kabir's Companion now-playing signal is 10 seconds old")
def fresh_np(kabir, fake_redis):
    put_signal(fake_redis, "np", kabir.pk, observed_at=NOW_TS - 10, via="COMPANION",
               platform="YOUTUBE_MUSIC")


@when("his card is rendered")
def render(kabir, ctx):
    client = APIClient()
    client.force_authenticate(kabir)
    with time_machine.travel(NOW, tick=False):
        resp = client.get("/api/v1/me/card")
    assert resp.status_code == 200
    ctx["raw"] = resp.content.decode()
    ctx["card"] = json.loads(ctx["raw"])


@then("its state is RECENT or TOP and never LIVE")
def not_live(ctx):
    assert ctx["card"]["state"] in {"RECENT", "TOP"}


@then(parsers.parse('its state is RECENT with label "{label}"'))
def recent_with_label(ctx, label):
    assert ctx["card"]["state"] == "RECENT"
    assert ctx["card"]["freshness_label"].startswith(label), ctx["card"]["freshness_label"]
    assert ctx["card"]["freshness_label"] == f"{label} on Spotify"


@then("its state is LIVE")
def is_live(ctx):
    assert ctx["card"]["state"] == "LIVE"
    assert ctx["card"]["freshness_label"] == "Live on YouTube Music"


@then('no "via" key appears anywhere in the card JSON')
def no_via(ctx):
    assert not _has_key(ctx["card"], "via")
    for word in ("COMPANION", "LISTENBRAINZ", "LASTFM", "DIRECT", "EXPORT"):
        assert word not in ctx["raw"]
