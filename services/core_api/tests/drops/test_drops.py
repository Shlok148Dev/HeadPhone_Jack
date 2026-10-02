"""JNG-14-01 Daily Drop: one a day, revealed after you drop, streaks, blocks, demo personas."""

from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.services import create_account
from drops import services
from drops.models import Drop
from social import services as social

pytestmark = pytest.mark.django_db


def mk(name):
    return create_account(
        email=f"{name}@x.test",
        password="password-1234",
        username=name,
        display_name=name.title(),
        birth_year=2000,
    )


def client(u):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(u)}")
    return c


def friends(a, b):
    social.accept(b, social.send_request(a, b))


def test_locked_until_you_drop_then_revealed():
    me, aanya, stranger = mk("me"), mk("aanya"), mk("stranger")
    friends(me, aanya)
    services.create(aanya, title="Kasoor", artist="Prateek Kuhad", note="on repeat")
    services.create(stranger, title="Yellow", artist="Coldplay")
    t = client(me).get("/api/v1/drops/today").json()
    assert t["locked"] is True and t["mine"] is None and t["friends"] == []
    assert [p["username"] for p in t["dropped"]] == ["aanya"]  # who, never what
    assert "Kasoor" not in str(t)
    r = client(me).post(
        "/api/v1/drops", {"title": "Baarishein", "artist": "Anuv Jain"}, format="json"
    )
    assert r.status_code == 201 and r.json()["title"] == "Baarishein"
    t = client(me).get("/api/v1/drops/today").json()
    assert t["locked"] is False and t["mine"]["title"] == "Baarishein" and t["streak"] == 1
    assert [d["title"] for d in t["friends"]] == ["Kasoor"]  # strangers never appear
    assert t["friends"][0]["note"] == "on repeat" and "SPOTIFY" in t["friends"][0]["search_links"]


def test_one_drop_per_day_and_validation():
    me = mk("solo")
    c = client(me)
    assert c.post("/api/v1/drops", {"title": "A", "artist": "B"}, format="json").status_code == 201
    r = c.post("/api/v1/drops", {"title": "C", "artist": "D"}, format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "ALREADY_DROPPED"
    assert (
        client(mk("v"))
        .post("/api/v1/drops", {"title": "", "artist": "B"}, format="json")
        .status_code
        == 400
    )
    assert (
        client(mk("w"))
        .post("/api/v1/drops", {"title": "A", "artist": "B", "note": "x" * 141}, format="json")
        .status_code
        == 400
    )


def test_unauthenticated_is_rejected():
    assert APIClient().get("/api/v1/drops/today").status_code == 401


def test_streak_counts_consecutive_days_and_survives_until_tonight():
    me = mk("streaky")
    today = services.today_for(me)
    for back in (1, 2, 3, 5):
        Drop.objects.create(user=me, day=today - timedelta(days=back), title="t", artist="a")
    assert services.streak(me) == 3  # yesterday, -2, -3 (today still open); -5 is after a gap
    services.create(me, title="Now", artist="X")
    assert services.streak(me) == 4


def test_blocked_friend_drops_disappear():
    me, b = mk("blk1"), mk("blk2")
    friends(me, b)
    services.create(b, title="Song", artist="Art")
    services.create(me, title="Mine", artist="Me")
    assert len(client(me).get("/api/v1/drops/today").json()["friends"]) == 1
    social.block(me, b)
    t = client(me).get("/api/v1/drops/today").json()
    assert t["friends"] == [] and t["dropped"] == []


def test_day_follows_the_users_timezone():
    me = mk("tzuser")
    from notifications.models import NotificationPrefs

    NotificationPrefs.objects.update_or_create(user=me, defaults={"tz": "America/Los_Angeles"})
    late_utc = datetime(2026, 10, 2, 3, 0, tzinfo=UTC)  # still 1 Oct in Los Angeles
    assert services.today_for(me, late_utc).isoformat() == "2026-10-01"


def test_demo_personas_drop_at_their_hour(settings, monkeypatch):
    from drops import tasks

    settings.JINGLE_DEMO = True
    from jingle_common.demo import PERSONAS

    for p in PERSONAS[:3]:
        mk(p.username)
    monkeypatch.setattr(tasks, "_h", lambda *a: 0)  # drop hour 06:00, first favourite
    late = datetime(2026, 10, 2, 16, 0, tzinfo=UTC)  # 21:30 IST
    monkeypatch.setattr(tasks.timezone, "now", lambda: late)
    monkeypatch.setattr(services.timezone, "now", lambda: late)
    assert tasks.demo_drops() == 3
    assert tasks.demo_drops() == 0  # idempotent within the day
    settings.JINGLE_DEMO = False
    assert tasks.demo_drops() == 0
