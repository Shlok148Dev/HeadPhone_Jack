"""JNG-15-01/02 Song and Artist of the Week: breadth over loops, privacy, merges, movement, fans."""

from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import ActivityVisibility, PrivacySettings
from charts import services
from social import services as social
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 10, 7, 9, 0, tzinfo=UTC)  # Wednesday; the week starts Monday 5 Oct (IST)
THIS_WEEK = NOW - timedelta(days=1)
LAST_WEEK = NOW - timedelta(days=8)


def person(name, **kw):
    u = UserFactory(username=name, display_name=name.title(), **kw)
    u.date_joined = NOW - timedelta(days=30)
    u.save(update_fields=["date_joined"])
    return u


def friends(a, b):
    social.accept(b, social.send_request(a, b))


def play(db, user, artist, title, n=1, at=THIS_WEEK, **extra):
    for i in range(n):
        db.listens.insert_one(
            {
                "meta": {"user_id": str(user.pk)},
                "played_at": at + timedelta(minutes=i),
                "raw": {"artist": artist, "title": title},
                **extra,
            }
        )


def charts_for(viewer, *everyone):
    for u in everyone:
        services.refresh_user(u, now=NOW)
    services.invalidate()
    return services.weekly(viewer, now=NOW)


@pytest.fixture
def crew(mongo_db):
    me = person("me")
    pals = [person(n) for n in ("aanya", "kabir", "meera", "dev", "riya")]
    for p in pals:
        friends(me, p)
    return me, pals


def test_breadth_beats_one_friend_looping(crew, mongo_db):
    me, pals = crew
    for p in pals:  # five friends, once each
        play(mongo_db, p, "Prateek Kuhad", "Kasoor")
    play(mongo_db, pals[0], "The Weeknd", "Blinding Lights", n=20)  # one friend, twenty times
    c = charts_for(me, me, *pals)
    assert c["enough"] is True and c["contributors"] == 5
    assert [s["title"] for s in c["songs"][:2]] == ["Kasoor", "Blinding Lights"]
    assert c["songs"][0]["listeners"] == 5
    # Daily cap: twenty plays in one day count as three.
    assert c["songs"][1]["plays"] == services.DAILY_CAP


def test_privacy_strangers_hidden_blocked_and_spotify_api_data_never_count(crew, mongo_db):
    me, pals = crew
    stranger = person("stranger")
    hidden, blocked = pals[3], pals[4]
    ps = PrivacySettings.for_user(hidden)
    ps.activity_visibility = ActivityVisibility.NOBODY
    ps.save()
    social.block(me, blocked)
    for u in (stranger, hidden, blocked):
        play(mongo_db, u, "Secret Band", "Leak", n=3)
    play(mongo_db, pals[0], "Spotify API", "Display Only", n=3, analytics_allowed=False)
    play(mongo_db, pals[1], "Prateek Kuhad", "Kasoor")
    c = charts_for(me, me, stranger, *pals)
    titles = {s["title"] for s in c["songs"]}
    assert titles == {"Kasoor"}
    assert all(a["name"] != "Secret Band" for a in c["artists"])


def test_same_song_from_different_apps_merges(crew, mongo_db):
    me, pals = crew
    play(mongo_db, pals[0], "Prateek Kuhad", "Kasoor")
    play(mongo_db, pals[1], "PRATEEK KUHAD", "kasoor")
    play(mongo_db, pals[2], "Prateek Kuhad", "Kasoor (feat. Nobody)")
    c = charts_for(me, me, *pals)
    assert len(c["songs"]) == 1 and c["songs"][0]["listeners"] == 3


def test_featured_artists_get_half_credit(crew, mongo_db):
    me, pals = crew
    for p in pals:  # five friends play the collab: Lead 1.0 each, Guest 0.5 each
        play(mongo_db, p, "Lead feat. Guest", "Collab")
    play(mongo_db, pals[0], "Guest", "Solo")
    c = charts_for(me, me, *pals)
    names = [a["name"] for a in c["artists"]]
    assert names[0] == "Lead" and names[1] == "Guest"
    guest = next(a for a in c["artists"] if a["name"] == "Guest")
    assert guest["listeners"] == 5 and guest["plays"] == round(5 * services.FEAT_CREDIT + 1)


def test_movement_new_entries_and_found_first(crew, mongo_db):
    me, pals = crew
    # Last week: B was #1, A #2.
    for p in pals[:3]:
        play(mongo_db, p, "Artist B", "B", at=LAST_WEEK)
    play(mongo_db, pals[0], "Artist A", "A", at=LAST_WEEK)
    # This week: A climbs to #1 (Riya first), B drops, C is new.
    play(mongo_db, pals[4], "Artist A", "A", at=THIS_WEEK - timedelta(hours=5))
    for p in pals[:4]:
        play(mongo_db, p, "Artist A", "A")
    for p in pals[:2]:
        play(mongo_db, p, "Artist B", "B")
    play(mongo_db, pals[3], "Artist C", "C")
    c = charts_for(me, me, *pals)
    by = {s["title"]: s for s in c["songs"]}
    assert by["A"]["rank"] == 1 and by["A"]["movement"] == {"kind": "up", "by": 1}
    assert by["B"]["movement"] == {"kind": "down", "by": 1}
    assert by["C"]["movement"]["kind"] == "new"
    assert by["A"]["found_first"]["username"] == "riya"


def test_new_fans_are_first_plays_this_week(crew, mongo_db):
    me, pals = crew
    play(mongo_db, pals[0], "Anuv Jain", "Husn", at=NOW - timedelta(days=60))  # long-time fan
    for p in pals[:3]:
        play(mongo_db, p, "Anuv Jain", "Husn")
    for u in (me, *pals):
        services.refresh_user(u, now=NOW, full=True)
    services.invalidate()
    c = services.weekly(me, now=NOW)
    anuv = next(a for a in c["artists"] if a["name"] == "Anuv Jain")
    assert {p["username"] for p in anuv["new_fans"]} == {"kabir", "meera"}


def test_brand_new_accounts_and_too_little_listening(mongo_db):
    me = person("solo")
    newbie = UserFactory(username="newbie")
    newbie.date_joined = NOW - timedelta(hours=2)  # joined two hours ago
    newbie.save(update_fields=["date_joined"])
    friends(me, newbie)
    play(mongo_db, newbie, "Fresh", "Gaming", n=3, at=NOW - timedelta(hours=1))
    c = charts_for(me, me, newbie)
    assert c["songs"] == [] and c["enough"] is False


def test_api_shape_auth_and_cache_invalidation(crew, mongo_db):
    me, pals = crew
    for p in pals[:3]:
        play(mongo_db, p, "Prateek Kuhad", "Kasoor", at=datetime.now(UTC) - timedelta(minutes=5))
    for u in (me, *pals):
        services.refresh_user(u)
    services.invalidate()
    c = APIClient()
    assert c.get("/api/v1/charts/weekly").status_code == 401
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(me)}")
    body = c.get("/api/v1/charts/weekly").json()
    s = body["songs"][0]
    assert s["title"] == "Kasoor" and s["rank"] == 1 and "SPOTIFY" in s["search_links"]
    assert {"links", "people", "movement", "you_played", "artwork_url"} <= set(s)
    assert (
        body["artists"][0]["name"] == "Prateek Kuhad"
        and body["artists"][0]["top_song"]["title"] == "Kasoor"
    )
    assert c.get("/api/v1/charts/weekly", {"week": "nope"}).status_code == 400
    # A friendship change clears cached charts (who counts as "your people" changed).
    from core_api.redis_client import get_redis

    assert list(get_redis().scan_iter("charts:v1:*"))
    social.remove_friend(me, pals[0].pk)
    assert not list(get_redis().scan_iter("charts:v1:*"))
