"""Live sessions (EP-07: JNG-07-05…09) incl. Gherkin: tests/features/ep07/JNG-07_live_queue.feature.

Real parallel voting against PostgreSQL is exercised end to end in
apps/web/e2e/ep07/JNG-07.spec.ts; here the rules and the broadcast contract are checked.
"""

import json

import pytest
from django.utils import timezone
from pytest_bdd import given, scenarios, then, when
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.services import create_account
from circles import services as circles
from listening import services
from listening.models import ListeningSession, Vote
from social import services as social

pytestmark = pytest.mark.django_db
scenarios("../features/ep07/JNG-07_live_queue.feature")


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


def room(n=3):
    host = mk("host")
    people = [mk(f"p{i}") for i in range(n - 1)]
    for p in people:
        befriend(host, p)
    s = services.start(host, user_ids=[str(p.pk) for p in people])
    for p in people:
        services.join(s, p)
    return s, host, people


def add(s, user, title, anonymous=False, key=None):
    return services.add(s, user, {"title": title, "artist": "Artist"}, anonymous, key or title)


# ---- Gherkin ------------------------------------------------------------------------------


@given("30 participants are in a session", target_fixture="ctx")
def _thirty():
    s, host, people = room(30)
    entry = add(s, host, "Kesariya")
    add(s, host, "Excuses")
    return {"s": s, "people": people, "entry": entry}


@when("10 of them vote on the same track within one second")
def _ten_votes(ctx):
    for p in ctx["people"][:10]:
        services.vote(ctx["entry"].pk, p, 1)


@then("all 10 votes count")
def _counted(ctx):
    ctx["entry"].refresh_from_db()
    assert ctx["entry"].score == 10
    assert Vote.objects.filter(entry=ctx["entry"]).count() == 10


@then("every participant sees the same order within 1 second at p95")
def _same_order(ctx):
    # One public state per change, stamped with a strictly increasing version: every client
    # applies the newest and converges on the same order (latency is measured by k6 in S11).
    state = services.public_state(ctx["s"])
    assert [e["title"] for e in state["queue"]] == ["Kesariya", "Excuses"]
    v1 = services.broadcast(ctx["s"])
    v2 = services.broadcast(ctx["s"])
    assert v2 == v1 + 1


@given("my connection drops for 20 seconds", target_fixture="ctx")
def _drop():
    s, host, people = room(3)
    add(s, host, "One")
    return {"s": s, "me": people[0], "host": host, "seen": services.current_version(s)}


@when("it returns")
def _returns(ctx):
    add(ctx["s"], ctx["host"], "Two")  # changed while I was away
    ctx["state"] = client(ctx["me"]).get(f"/api/v1/sessions/{ctx['s'].pk}").json()


@then("my queue matches the server's within 2 seconds")
def _matches(ctx):
    assert ctx["state"]["version"] > ctx["seen"]  # the gap tells the client to take this state
    assert [e["title"] for e in ctx["state"]["queue"]] == ["One", "Two"]
    assert ctx["state"]["joined"] is True


# ---- rules --------------------------------------------------------------------------------


def test_JNG_07_05_start_and_invite_friends_or_circle():
    host, f, stranger = mk("host"), mk("frnd"), mk("strn")
    befriend(host, f)
    c = client(host)
    r = c.post("/api/v1/sessions", {"user_ids": [str(f.pk)]}, format="json")
    assert r.status_code == 201 and r.json()["title"] == "Host's session"
    sid = r.json()["id"]
    assert client(f).get("/api/v1/sessions").json()[0]["joined"] is False
    assert client(f).post(f"/api/v1/sessions/{sid}/join").json()["joined"] is True
    assert client(stranger).get(f"/api/v1/sessions/{sid}").status_code == 404
    assert (
        c.post("/api/v1/sessions", {"user_ids": [str(stranger.pk)]}, format="json").status_code
        == 404
    )
    circle = circles.create_circle(host, "Crew")
    token, _ = circles.create_link(circle, host)
    circles.join_by_link(token, stranger)
    s2 = c.post("/api/v1/sessions", {"circle_id": str(circle.pk)}, format="json").json()
    assert s2["title"] == "Crew session"
    assert client(stranger).post(f"/api/v1/sessions/{s2['id']}/join").status_code == 200


def test_JNG_07_06_anonymous_add_hides_the_adder_and_is_idempotent():
    s, host, (p, *_rest) = room(3)
    c = client(p)
    body = {
        "title": "Kasoor",
        "artist": "Prateek Kuhad",
        "anonymous": True,
        "idempotency_key": "k1",
    }
    e1 = c.post(f"/api/v1/sessions/{s.pk}/queue", body, format="json").json()
    e2 = c.post(f"/api/v1/sessions/{s.pk}/queue", body, format="json").json()
    assert e1["id"] == e2["id"] and e1["added_by"] is None
    state = client(host).get(f"/api/v1/sessions/{s.pk}").json()
    assert state["queue"][0]["added_by"] is None and "submitted_by" not in json.dumps(state)
    named = c.post(
        f"/api/v1/sessions/{s.pk}/queue",
        {"title": "Blue", "artist": "Yung Kai", "idempotency_key": "k2"},
        format="json",
    ).json()
    assert named["added_by"]["username"] == p.username
    assert (
        c.post(
            f"/api/v1/sessions/{s.pk}/queue", {"title": "x", "artist": "y"}, format="json"
        ).status_code
        == 400
    )


def test_JNG_07_07_one_vote_each_reorders_and_withdraws():
    s, host, (a, b) = room(3)
    first, second = add(s, host, "First"), add(s, host, "Second")
    for u in (a, b):
        assert (
            client(u)
            .post(f"/api/v1/queue/{second.pk}/vote", {"value": 1}, format="json")
            .json()["score"]
            >= 1
        )
    client(a).post(
        f"/api/v1/queue/{second.pk}/vote", {"value": 1}, format="json"
    )  # again: still one
    second.refresh_from_db()
    assert second.score == 2
    state = client(a).get(f"/api/v1/sessions/{s.pk}").json()
    assert [e["title"] for e in state["queue"]] == ["Second", "First"]
    assert state["my_votes"] == {str(second.pk): 1}
    client(a).post(f"/api/v1/queue/{second.pk}/vote", {"value": -1}, format="json")
    client(b).post(f"/api/v1/queue/{second.pk}/vote", {"value": 0}, format="json")
    second.refresh_from_db()
    assert second.score == -1
    assert (
        client(a).post(f"/api/v1/queue/{first.pk}/vote", {"value": 5}, format="json").status_code
        == 400
    )
    outsider = mk("outs")
    assert (
        client(outsider)
        .post(f"/api/v1/queue/{first.pk}/vote", {"value": 1}, format="json")
        .status_code
        == 404
    )


def test_next_is_host_only_and_moves_the_top_track_to_now_playing():
    s, host, (a, _b) = room(3)
    add(s, host, "One")
    assert client(a).post(f"/api/v1/sessions/{s.pk}/next").status_code == 403
    state = client(host).post(f"/api/v1/sessions/{s.pk}/next").json()
    assert state["now_playing"]["title"] == "One" and state["queue"] == []
    assert "search_links" in state["now_playing_links"]


def test_JNG_07_08_survives_the_host_leaving(fake_redis):
    s, host, (a, b) = room(3)
    fake_redis.set(f"sesspres:{s.pk}:{b.pk}", "1")  # b online, a not
    client(host).post(f"/api/v1/sessions/{s.pk}/leave")
    s.refresh_from_db()
    assert s.ended_at is None and s.host_id == b.pk
    # A host who silently drops off hands over on the next sweep.
    fake_redis.set(f"sesspres:{s.pk}:{a.pk}", "1")
    fake_redis.delete(f"sesspres:{s.pk}:{b.pk}")
    assert services.sweep()["handed_over"] == 1
    s.refresh_from_db()
    assert s.host_id == a.pk


def test_last_person_out_ends_and_idle_rooms_end(fake_redis):
    s, host, (a,) = room(2)
    client(a).post(f"/api/v1/sessions/{s.pk}/leave")
    client(host).post(f"/api/v1/sessions/{s.pk}/leave")
    s.refresh_from_db()
    assert s.ended_at is not None
    host2 = mk("host2")
    s2 = services.start(host2)
    ListeningSession.objects.filter(pk=s2.pk).update(
        created_at=timezone.now() - services.IDLE_END * 2
    )
    assert services.sweep(timezone.now())["ended"] == 1


def test_broadcast_carries_public_state_and_version(fake_redis, django_capture_on_commit_callbacks):
    s, host, _ = room(2)
    with django_capture_on_commit_callbacks(execute=True):
        add(s, host, "Song", anonymous=True)
    entries = [f for _i, f in fake_redis.xrange("events:domain") if f.get("type") == "queue.delta"]
    assert entries
    last = json.loads(entries[-1]["data"])
    state = json.loads(last["state"])
    assert last["session_id"] == str(s.pk) and last["version"] >= 2
    assert state["queue"][0]["added_by"] is None


def test_internal_member_check_for_realtime(settings):
    s, host, (a,) = room(2)
    x = mk("xx")
    url = "/internal/sessions/{}/members/{}"
    h = {"HTTP_X_SERVICE_TOKEN": settings.SERVICE_TOKEN}
    assert APIClient().get(url.format(s.pk, a.pk), **h).status_code == 200
    assert APIClient().get(url.format(s.pk, x.pk), **h).status_code == 404
    assert APIClient().get(url.format(s.pk, a.pk)).status_code in (401, 403)
