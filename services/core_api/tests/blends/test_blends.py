"""Blends (EP-07: JNG-07-01…04)."""

from collections import Counter
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import ActivityVisibility, PrivacySettings
from accounts.services import create_account
from blends import engine
from blends.models import BlendTrack
from circles import services as circles
from social import services as social

pytestmark = pytest.mark.django_db


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


def plays(db, user, artist, title, n=1, **extra):
    for i in range(n):
        db.listens.insert_one(
            {
                "meta": {"user_id": str(user.pk)},
                "played_at": timezone.now() - timedelta(days=1, minutes=i),
                "raw": {"artist": artist, "title": title},
                **extra,
            }
        )


# ---- engine (Tech Bible 6.2) --------------------------------------------------------------


def catalog(*tracks):
    return {
        f"{a.lower()}|{t.lower()}": engine.Track(f"{a.lower()}|{t.lower()}", t, a)
        for a, t in tracks
    }


def test_group_utility_prefers_shared_tracks_and_explains_them():
    cat = catalog(
        ("Arijit Singh", "Kesariya"), ("Prateek Kuhad", "Kasoor"), ("AP Dhillon", "Excuses")
    )
    a = engine.Member(
        "a", "Aanya", Counter({"arijit singh|kesariya": 5, "prateek kuhad|kasoor": 9})
    )
    k = engine.Member("k", "Kabir", Counter({"arijit singh|kesariya": 4, "ap dhillon|excuses": 9}))
    out = engine.generate([a, k], cat)
    assert out[0].track.title == "Kesariya"  # both love it: beats one-sided favourites
    assert out[0].reason == "Aanya and Kabir both play this"
    assert all(p.reason for p in out)


def test_constraints_two_per_artist_and_40_percent_share():
    tracks = [("Solo", f"S{i}") for i in range(10)] + [(f"Art{i}", f"T{i}") for i in range(40)]
    cat = catalog(*tracks)
    heavy = engine.Member("h", "Heavy", Counter({k: 100 for k in cat}))
    light = engine.Member("l", "Light", Counter({k: 1 for k in list(cat)[10:25]}))
    out = engine.generate([heavy, light], cat)
    assert len(out) == engine.SIZE
    assert Counter(p.track.artist for p in out)["Solo"] <= engine.MAX_PER_ARTIST
    assert len({p.track.key for p in out}) == len(out)


def test_pins_are_kept_first():
    cat = catalog(("A", "One"), ("B", "Two"))
    m = [
        engine.Member("a", "Ana", Counter({"a|one": 3})),
        engine.Member("b", "Ben", Counter({"b|two": 3})),
    ]
    pin = engine.Pick(engine.Track("x|pinned", "Pinned", "X"), "Pinned by Ana", ["a"], pinned=True)
    out = engine.generate(m, cat, [pin])
    assert out[0] is pin and {p.track.title for p in out} == {"Pinned", "One", "Two"}


def test_reason_names_a_fan_of_the_artist():
    cat = catalog(("Prateek Kuhad", "Kasoor"), ("Prateek Kuhad", "cold/mess"))
    a = engine.Member("a", "Aanya", Counter({"prateek kuhad|kasoor": 5}))
    k = engine.Member("k", "Kabir", Counter({"prateek kuhad|cold/mess": 5}))
    reasons = {p.track.title: p.reason for p in engine.generate([a, k], cat)}
    assert reasons["Kasoor"] == "From Aanya's top plays; Kabir plays a lot of Prateek Kuhad"


# ---- API + privacy ------------------------------------------------------------------------


def test_JNG_07_01_02_blend_with_friends_has_reasons(mongo_db):
    a, b = mk("aanya"), mk("kabir")
    befriend(a, b)
    plays(mongo_db, a, "Arijit Singh", "Kesariya", 3)
    plays(mongo_db, b, "Arijit Singh", "Kesariya", 2)
    plays(mongo_db, b, "AP Dhillon", "Excuses", 4)
    plays(mongo_db, b, "Secret", "Spotify only", 9, analytics_allowed=False)  # BR-03: never used
    r = client(a).post("/api/v1/blends", {"user_ids": [str(b.pk)]}, format="json")
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Aanya + Kabir"
    titles = [t["title"] for t in body["tracks"]]
    assert titles[0] == "Kesariya" and "Spotify only" not in titles
    assert all(t["reason"] for t in body["tracks"])
    assert body["save"]["available"] is False  # JNG-07-04: honest
    assert client(b).get("/api/v1/blends").json()[0]["id"] == body["id"]


def test_blend_needs_friends_and_2_to_6_people():
    a, b, x = mk("aanya"), mk("kabir"), mk("xavi")
    befriend(a, b)
    c = client(a)
    assert c.post("/api/v1/blends", {"user_ids": [str(x.pk)]}, format="json").status_code == 404
    assert c.post("/api/v1/blends", {"user_ids": []}, format="json").status_code == 400
    many = [mk(f"f{i}") for i in range(6)]
    for f in many:
        befriend(a, f)
    assert (
        c.post("/api/v1/blends", {"user_ids": [str(f.pk) for f in many]}, format="json").status_code
        == 400
    )
    assert (
        client(x)
        .get(
            f"/api/v1/blends/{c.post('/api/v1/blends', {'user_ids': [str(b.pk)]}, format='json').json()['id']}"
        )
        .status_code
        == 404
    )


def test_member_whose_plays_others_cannot_see_is_left_out(mongo_db):
    """A (friends with B and C); B and C are strangers: B's plays would leak to C."""
    a, b, c = mk("aanya"), mk("bala"), mk("cai")
    befriend(a, b)
    befriend(a, c)
    plays(mongo_db, a, "Arijit Singh", "Kesariya", 2)
    plays(mongo_db, b, "Hidden", "Bala song", 5)
    plays(mongo_db, c, "Hidden", "Cai song", 5)
    body = (
        client(a).post("/api/v1/blends", {"user_ids": [str(b.pk), str(c.pk)]}, format="json").json()
    )
    assert {p["username"] for p in body["left_out"]} == {"bala", "cai"}
    assert [t["title"] for t in body["tracks"]] == ["Kesariya"]


def test_circle_blend_respects_circles_visibility(mongo_db):
    o, m = mk("own"), mk("mem")
    circle = circles.create_circle(o, "Crew")
    token, _ = circles.create_link(circle, o)
    circles.join_by_link(token, m)
    ps = PrivacySettings.for_user(m)
    ps.activity_visibility = ActivityVisibility.CIRCLES
    ps.save()
    plays(mongo_db, m, "Prateek Kuhad", "Kasoor", 3)
    body = client(o).post("/api/v1/blends", {"circle_id": str(circle.pk)}, format="json").json()
    assert body["name"] == "Crew Blend" and body["circle"]["name"] == "Crew"
    assert [t["title"] for t in body["tracks"]] == ["Kasoor"]
    # The owner's default visibility is "friends": a non-friend co-member mustn't see their plays.
    assert [p["username"] for p in body["left_out"]] == ["own"]


def test_JNG_07_03_regenerate_keeps_pins(mongo_db):
    a, b = mk("aanya"), mk("kabir")
    befriend(a, b)
    plays(mongo_db, a, "Arijit Singh", "Kesariya", 3)
    plays(mongo_db, b, "AP Dhillon", "Excuses", 3)
    body = client(a).post("/api/v1/blends", {"user_ids": [str(b.pk)]}, format="json").json()
    excuses = next(t for t in body["tracks"] if t["title"] == "Excuses")
    url = f"/api/v1/blends/{body['id']}/tracks/{excuses['id']}/pin"
    assert client(a).post(url).json()["pinned"] is True
    mongo_db.listens.delete_many({"raw.title": "Excuses"})  # it would no longer be picked
    again = client(b).post(f"/api/v1/blends/{body['id']}/regenerate").json()
    kept = next(t for t in again["tracks"] if t["title"] == "Excuses")
    assert kept["pinned"] and kept["reason"] == "Pinned by Aanya"
    assert again["tracks"][0]["title"] == "Excuses"
    t = BlendTrack.objects.get(pk=kept["id"])
    assert (
        client(a).delete(f"/api/v1/blends/{body['id']}/tracks/{t.pk}/pin").json()["pinned"] is False
    )


def test_leaving_last_pair_removes_blend(mongo_db):
    a, b = mk("aanya"), mk("kabir")
    befriend(a, b)
    bid = client(a).post("/api/v1/blends", {"user_ids": [str(b.pk)]}, format="json").json()["id"]
    assert client(b).delete(f"/api/v1/blends/{bid}").status_code == 204
    assert client(a).get(f"/api/v1/blends/{bid}").status_code == 404
