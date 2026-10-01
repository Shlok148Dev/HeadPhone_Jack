"""Compatibility, stats and timeline (EP-08) incl. Gherkin: features/ep08/JNG-08_explained_score.feature."""

import json
from collections import Counter
from datetime import timedelta

import pytest
from django.utils import timezone
from pytest_bdd import given, scenarios, then, when
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import ActivityVisibility, PrivacySettings
from accounts.services import create_account
from insights import compute
from social import services as social
from sources.models import Artist, ArtistTag

pytestmark = pytest.mark.django_db
scenarios("../features/ep08/JNG-08_explained_score.feature")


def mk(name):
    return create_account(
        email=f"{name}@x.test",
        username=name,
        password="password-1234",
        display_name=name.title(),
        birth_year=1999,
    )


def client(u):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(u)}")
    return c


def befriend(a, b):
    social.accept(b, social.send_request(a, b))


def plays(db, user, artist, n, days_ago=1, **extra):
    db.listens.insert_many(
        [
            {
                "meta": {"user_id": str(user.pk), "platform": "YOUTUBE_MUSIC"},
                "played_at": timezone.now() - timedelta(days=days_ago, minutes=i),
                "raw": {"artist": artist, "title": f"T{i}", "duration_ms": 180_000},
                **extra,
            }
            for i in range(n)
        ]
    )


def tag(name, *tags):
    a = Artist.objects.create(name=name)
    for t in tags:
        ArtistTag.objects.create(artist=a, tag=t, weight=1.0)


# ---- Gherkin ------------------------------------------------------------------------------


@given("neither friend has tracks with analysed preview audio", target_fixture="ctx")
def _no_audio(mongo_db):
    a, b = mk("aanya"), mk("kabir")
    befriend(a, b)
    plays(mongo_db, a, "Arijit Singh", 15)
    plays(mongo_db, a, "Pritam", 10)
    plays(mongo_db, b, "Arijit Singh", 12)
    plays(mongo_db, b, "AP Dhillon", 12)
    tag("Arijit Singh", "bollywood")
    tag("Pritam", "bollywood")
    tag("AP Dhillon", "punjabi")
    return {"a": a, "b": b}


@when("the score is shown")
def _shown(ctx):
    ctx["body"] = client(ctx["a"]).get(f"/api/v1/compatibility/{ctx['b'].pk}").json()


@then('the breakdown says "Sound comparison unavailable" and no audio numbers appear')
def _no_sound(ctx):
    body = ctx["body"]
    assert body["ready"] and isinstance(body["score"], int)
    assert "Sound comparison unavailable" in body["notes"]
    assert body["audio_features_available"] is False
    assert [f["key"] for f in body["breakdown"]] == ["artists", "genres"]  # BR-09: never bare
    assert "sound" not in json.dumps(body["breakdown"]).lower()
    assert body["shared_artists"] == ["Arijit Singh"] and "bollywood" in body["shared_genres"]


# ---- formula (Tech Bible 6.1) -------------------------------------------------------------


def test_weighted_jaccard_and_weights():
    assert compute.weighted_jaccard({"a": 0.5, "b": 0.5}, {"a": 0.5, "b": 0.5}) == 1.0
    assert compute.weighted_jaccard({"a": 1.0}, {"b": 1.0}) == 0.0
    assert compute.weighted_jaccard(
        {"a": 0.75, "b": 0.25}, {"a": 0.25, "b": 0.75}
    ) == pytest.approx(0.5 / 1.5)
    u = Counter({"x": 30})
    v = Counter({"x": 30})
    tags = {"x": {"pop": 1.0}}
    c = compute.compatibility(u, v, {}, tags)
    assert c.raw == pytest.approx(1.0) and c.components["artists"]["weight"] == 0.6
    no_tags = compute.compatibility(u, v, {}, {})
    assert not no_tags.genres_available and no_tags.components == {
        "artists": {"value": 1.0, "weight": 1.0}
    }
    assert not compute.compatibility(Counter({"x": 5}), v, {}, tags).ready  # too little data


def test_percentile_calibrates_only_with_enough_pairs():
    assert compute.percentile(0.42, [0.1] * 5) == (42, False)
    dist = sorted([i / 100 for i in range(100)])
    assert compute.percentile(0.5, dist) == (50, True)
    assert compute.percentile(0.99, dist)[0] >= 98


def test_recalibrate_stores_numbers_only(mongo_db, fake_redis):
    a, b = mk("aanya"), mk("kabir")
    befriend(a, b)
    plays(mongo_db, a, "Arijit Singh", 25)
    plays(mongo_db, b, "Arijit Singh", 25)
    assert compute.recalibrate() == 1
    assert json.loads(fake_redis.get(compute.DIST_KEY)) == [1.0]


# ---- access + privacy ---------------------------------------------------------------------


def test_compatibility_only_for_friends_whose_activity_i_may_see(mongo_db):
    a, b, x = mk("aanya"), mk("kabir"), mk("xavi")
    befriend(a, b)
    assert client(a).get(f"/api/v1/compatibility/{x.pk}").status_code == 404
    assert client(a).get(f"/api/v1/compatibility/{a.pk}").status_code == 404
    ps = PrivacySettings.for_user(b)
    ps.activity_visibility = ActivityVisibility.NOBODY
    ps.save()
    assert client(a).get(f"/api/v1/compatibility/{b.pk}").status_code == 404
    ps.activity_visibility = ActivityVisibility.FRIENDS
    ps.save()
    body = client(a).get(f"/api/v1/compatibility/{b.pk}").json()
    assert body["ready"] is False and body["score"] is None and body["breakdown"] == []


def test_direct_spotify_listens_never_count(mongo_db):
    a, b = mk("aanya"), mk("kabir")
    befriend(a, b)
    plays(mongo_db, a, "Arijit Singh", 25, analytics_allowed=False)
    plays(mongo_db, b, "Arijit Singh", 25)
    assert client(a).get(f"/api/v1/compatibility/{b.pk}").json()["ready"] is False


# ---- my stats + timeline ------------------------------------------------------------------


def test_JNG_08_06_new_member_sees_building_state(mongo_db):
    a = mk("aanya")
    plays(mongo_db, a, "Arijit Singh", 3, days_ago=2)
    body = client(a).get("/api/v1/me/stats").json()
    assert body["ready"] is False and body["ready_in_days"] == compute.READY_DAYS - 2


def test_JNG_08_07_my_stats(mongo_db):
    a = mk("aanya")
    tag("Arijit Singh", "bollywood")
    plays(mongo_db, a, "Arijit Singh", 10, days_ago=1)
    plays(mongo_db, a, "Prateek Kuhad", 5, days_ago=2)
    plays(mongo_db, a, "Old", 5, days_ago=20)
    plays(mongo_db, a, "Spotify only", 4, days_ago=1, analytics_allowed=False)
    body = client(a).get("/api/v1/me/stats").json()
    assert body["ready"] is True and body["plays_30d"] == 20
    assert body["minutes_30d"] == 60  # 20 × 3 min
    assert body["top_artists"][0] == {"name": "Arijit Singh", "plays": 10}
    assert body["genres"][0]["name"] == "bollywood"
    assert body["platforms"] == [{"platform": "YOUTUBE_MUSIC", "share": 1.0}]
    assert body["excluded_note"]


def test_JNG_08_03_timeline_has_12_months(mongo_db):
    a = mk("aanya")
    plays(mongo_db, a, "Arijit Singh", 4, days_ago=1)
    plays(mongo_db, a, "Radiohead", 6, days_ago=70)
    months = client(a).get("/api/v1/me/timeline").json()
    assert len(months) == 12
    assert months[-1]["month"] == timezone.now().strftime("%Y-%m")
    recent = (timezone.now() - timedelta(days=1)).strftime("%Y-%m")  # month-boundary safe
    assert next(m for m in months if m["month"] == recent)["top_artist"] == "Arijit Singh"
    assert any(m["top_artist"] == "Radiohead" for m in months[:-1])
    assert len({m["month"] for m in months}) == 12


def test_profile_shows_fields_only_to_friends():
    a, b, x = mk("aanya"), mk("kabir"), mk("xavi")
    befriend(a, b)
    b.college = "KJ Somaiya"
    b.save()
    mine = client(b).get("/api/v1/users/kabir").json()
    assert mine["is_me"] is True and mine["college"] == "KJ Somaiya"
    friend = client(a).get("/api/v1/users/Kabir").json()
    assert friend["compatibility_available"] is True and friend["college"] == "KJ Somaiya"
    stranger = client(x).get("/api/v1/users/kabir").json()
    assert stranger["compatibility_available"] is False and stranger["college"] == ""
    social.block(b, x)
    assert client(x).get("/api/v1/users/kabir").status_code == 404
