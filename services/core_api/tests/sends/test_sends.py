"""Sends and mixtapes (EP-06) incl. Gherkin: tests/features/ep06/JNG-06_sends.feature."""

from datetime import timedelta

import pytest
from django.utils import timezone
from pytest_bdd import given, scenarios, then, when
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.services import create_account
from circles import services as circles
from core_api.errors import ApiError
from sends import services
from sends.models import Delivery, Recommendation
from social import services as social
from sources.models import Recording, RecordingLink

pytestmark = pytest.mark.django_db
scenarios("../features/ep06/JNG-06_sends.feature")

KASOOR = {"title": "Kasoor", "artist": "Prateek Kuhad"}


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


def rec(title="Kasoor", artist="Prateek Kuhad", isrc=None):
    return Recording.objects.create(
        title=title, artist_name=artist, isrc=isrc, norm_key=f"{artist}|{title}".lower()
    )


def post(user, body):
    return client(user).post("/api/v1/recommendations", body, format="json")


def listen(db, user, at, artist="Prateek Kuhad", title="Kasoor", **extra):
    db.listens.insert_one(
        {
            "meta": {"user_id": str(user.pk)},
            "played_at": at,
            "raw": {"artist": artist, "title": title},
            **extra,
        }
    )


def five_songs():
    return [{"title": f"Song {i}", "artist": f"Artist {i}"} for i in range(5)]


# ---- Gherkin ------------------------------------------------------------------------------


@given("Riya sends a track resolved to a Recording with an ISRC", target_fixture="ctx")
def _riya_sends():
    riya, dev = mk("riya"), mk("dev")
    befriend(riya, dev)
    r = rec(isrc="USUM72000001")
    RecordingLink.objects.create(
        recording=r, platform="SPOTIFY", url="https://open.spotify.com/track/abc"
    )
    RecordingLink.objects.create(
        recording=r, platform="APPLE_MUSIC", url="https://music.apple.com/in/song/1"
    )
    resp = post(riya, {"items": [{"recording_id": str(r.pk)}], "user_ids": [str(dev.pk)]})
    assert resp.status_code == 201
    return {"dev": dev}


@given("the Recording has no Apple Music link", target_fixture="ctx")
def _no_apple():
    riya, dev = mk("riya"), mk("dev")
    befriend(riya, dev)
    r = rec(title="Blue", artist="Yung Kai")
    RecordingLink.objects.create(
        recording=r, platform="SPOTIFY", url="https://open.spotify.com/track/xyz"
    )
    services.send(riya, [{"recording_id": str(r.pk)}], user_ids=[str(dev.pk)])
    return {"dev": dev}


@when("Dev, who uses Apple Music, opens it")
@when("Dev opens it")
def _dev_opens(ctx):
    ctx["item"] = client(ctx["dev"]).get("/api/v1/inbox").json()[0]["items"][0]


@then("the Open button deep-links to the Apple Music version")
def _deep_link(ctx):
    assert ctx["item"]["links"]["APPLE_MUSIC"] == "https://music.apple.com/in/song/1"


@then('he sees "Not found on Apple Music" and a search link')
def _search(ctx):
    # The web client says "Not found on Apple Music" when there is no verified link
    # (apps/web/src/lib/sends.test.ts).
    assert ctx["item"]["links"]["APPLE_MUSIC"] is None
    url = ctx["item"]["search_links"]["APPLE_MUSIC"]
    assert url.startswith("https://music.apple.com/search?term=") and "Blue" in url


# ---- rules --------------------------------------------------------------------------------


def test_JNG_06_01_track_with_note_to_friends_only():
    a, b, stranger = mk("anna"), mk("bala"), mk("str")
    befriend(a, b)
    ok = post(a, {"items": [KASOOR], "note": "for your commute", "user_ids": [str(b.pk)]})
    assert ok.status_code == 201 and ok.json()["recipients"] == 1
    assert post(a, {"items": [KASOOR], "user_ids": [str(stranger.pk)]}).status_code == 404
    assert (
        post(a, {"items": [KASOOR], "note": "a" * 281, "user_ids": [str(b.pk)]}).status_code == 400
    )
    none = post(a, {"items": [KASOOR]}).json()
    assert none["error"]["message"] == "Pick at least one friend or circle."
    assert post(a, {"items": [{"title": "x"}], "user_ids": [str(b.pk)]}).status_code == 400


def test_JNG_06_02_mixtape_is_5_to_8():
    a, b = mk("anna"), mk("bala")
    befriend(a, b)
    for n, ok in ((1, True), (2, False), (4, False), (5, True), (8, True), (9, False)):
        items = [{"title": f"S{i}", "artist": f"A{i}"} for i in range(n)]
        assert (post(a, {"items": items, "user_ids": [str(b.pk)]}).status_code == 201) is ok, n
    assert Recommendation.objects.filter(kind="mixtape").count() == 2
    dup = [{"title": "Same", "artist": "One"}] * 5
    assert post(a, {"items": dup, "user_ids": [str(b.pk)]}).status_code == 400


def test_send_to_circle_reaches_co_members_not_blocked():
    o, m1, m2 = mk("own"), mk("mem"), mk("blk")
    circle = circles.create_circle(o, "Crew")
    token, _ = circles.create_link(circle, o)
    circles.join_by_link(token, m1)
    circles.join_by_link(token, m2)
    social.block(m2, o)
    sent = services.send(o, five_songs(), circle_ids=[str(circle.pk)])
    assert {d.recipient_id for d in sent.deliveries.all()} == {m1.pk}
    assert sent.deliveries.get().circle_id == circle.pk
    with pytest.raises(ApiError):
        services.send(mk("xxx"), five_songs(), circle_ids=[str(circle.pk)])


def test_JNG_06_04_statuses_and_JNG_06_07_inbox(mongo_db):
    a, b = mk("anna"), mk("bala")
    befriend(a, b)
    r = rec()
    services.send(a, [{"recording_id": str(r.pk)}], note="listen", user_ids=[str(b.pk)])

    def status():
        return client(a).get("/api/v1/inbox/sent").json()[0]["recipients"][0]["status"]

    assert status() == "sent"
    assert client(b).get("/api/v1/inbox/unread").json() == {"count": 1}
    assert status() == "delivered"
    inbox = client(b).get("/api/v1/inbox").json()
    assert inbox[0]["note"] == "listen" and inbox[0]["sender"]["username"] == "anna"
    did = inbox[0]["id"]
    assert client(b).post(f"/api/v1/inbox/{did}/view").json()["status"] == "viewed"
    assert client(b).get("/api/v1/inbox/unread").json() == {"count": 0}
    assert client(a).post(f"/api/v1/inbox/{did}/view").status_code == 404  # not the recipient
    # Played only from Bala's own listens after the send, never from direct-Spotify data.
    after = timezone.now() + timedelta(minutes=1)
    listen(mongo_db, b, after, recording_id=str(r.pk), analytics_allowed=False)
    assert services.check_played() == 0
    listen(mongo_db, b, after, artist="prateek  kuhad", title="KASOOR", analytics_allowed=True)
    assert services.check_played() == 1
    assert status() == "played"


def test_played_ignores_listens_before_the_send(mongo_db):
    a, b = mk("anna"), mk("bala")
    befriend(a, b)
    listen(mongo_db, b, timezone.now() - timedelta(hours=1))
    services.send(a, [KASOOR], user_ids=[str(b.pk)])
    assert services.check_played() == 0


def test_JNG_06_06_react_and_reply_with_a_song():
    a, b, c = mk("anna"), mk("bala"), mk("cai")
    befriend(a, b)
    services.send(a, [KASOOR], user_ids=[str(b.pk)])
    d = Delivery.objects.get()
    url = f"/api/v1/inbox/{d.pk}/react"
    assert client(b).post(url, {"reaction": "🔥"}, format="json").json()["reaction"] == "🔥"
    assert client(b).post(url, {"reaction": "nope"}, format="json").status_code == 400
    assert client(c).post(url, {"reaction": "🔥"}, format="json").status_code == 404
    r = post(b, {"items": [{"title": "Blue", "artist": "Yung Kai"}], "reply_to": str(d.pk)})
    assert r.status_code == 201
    back = client(a).get("/api/v1/inbox").json()
    assert back[0]["is_reply"] is True and back[0]["items"][0]["title"] == "Blue"
    assert client(a).get("/api/v1/inbox/sent").json()[0]["recipients"][0]["reaction"] == "🔥"
    # Only the recipient can reply to a send.
    assert post(c, {"items": [KASOOR], "reply_to": str(d.pk)}).status_code == 404


def test_JNG_06_05_discovery_credit(mongo_db):
    a, b = mk("anna"), mk("bala")
    befriend(a, b)
    services.send(a, [KASOOR], user_ids=[str(b.pk)])
    services.mark_delivered(b)
    now = timezone.now() + timedelta(days=10)
    for i in range(3):
        listen(mongo_db, b, now - timedelta(days=i + 1), title=f"T{i}")
    assert services.discovery_credits(now) == 1
    got = client(a).get("/api/v1/inbox/sent").json()[0]["recipients"][0]
    assert got["credit_artist"] == "Prateek Kuhad"


def test_no_credit_when_artist_was_already_known(mongo_db):
    a, b = mk("anna"), mk("bala")
    befriend(a, b)
    listen(mongo_db, b, timezone.now() - timedelta(days=40), title="Old")
    services.send(a, [KASOOR], user_ids=[str(b.pk)])
    services.mark_delivered(b)
    now = timezone.now() + timedelta(days=5)
    listen(mongo_db, b, now - timedelta(days=1), title="New")
    assert services.discovery_credits(now) == 0


def test_block_hides_sends_both_ways():
    a, b = mk("anna"), mk("bala")
    befriend(a, b)
    services.send(a, [KASOOR], user_ids=[str(b.pk)])
    social.block(b, a)
    assert client(b).get("/api/v1/inbox").json() == []
    assert client(a).get("/api/v1/inbox/sent").json()[0]["recipients"] == []


def test_song_search_uses_known_recordings():
    a = mk("anna")
    rec(title="Tum Hi Ho", artist="Arijit Singh")
    rec(title="Kasoor", artist="Prateek Kuhad")
    got = client(a).get("/api/v1/songs/search", {"q": "arijit tum"}).json()
    assert [s["title"] for s in got] == ["Tum Hi Ho"]
    assert client(a).get("/api/v1/songs/search", {"q": "a"}).json() == []
