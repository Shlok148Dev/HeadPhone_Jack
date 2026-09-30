"""Circles (EP-04) incl. Gherkin: tests/features/ep04/JNG-04_circles.feature."""

from datetime import timedelta

import numpy as np
import pytest
from django.utils import timezone
from pytest_bdd import given, scenarios, then, when
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import ActivityVisibility, PrivacySettings
from accounts.services import create_account
from circles import services
from circles.models import Circle, CircleInvite, CircleMember, Role, SuggestedCircle
from core_api import policy
from social import services as social

pytestmark = pytest.mark.django_db
scenarios("../features/ep04/JNG-04_circles.feature")


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


# ---- Gherkin ------------------------------------------------------------------------------


@given("a circle has 50 members", target_fixture="ctx")
def _full():
    owner = mk("owner")
    c = services.create_circle(owner, "Big")
    for i in range(49):
        CircleMember.objects.create(circle=c, user=mk(f"m{i}"))
    Circle.objects.filter(pk=c.pk).update(member_count=50)
    token, _ = services.create_link(c, owner)
    return {"circle": c, "token": token, "late": mk("late")}


@when("someone opens its invite link")
def _open(ctx):
    ctx["preview"] = APIClient().get(f"/api/v1/circles/join/{ctx['token']}").json()
    ctx["resp"] = client(ctx["late"]).post(f"/api/v1/circles/join/{ctx['token']}")


@then('they see "This circle is full" and are not added')
def _not_added(ctx):
    assert ctx["preview"]["full"] is True
    assert ctx["resp"].status_code == 409
    assert ctx["resp"].json()["error"]["message"] == "This circle is full"
    assert not CircleMember.objects.filter(circle=ctx["circle"], user=ctx["late"]).exists()


@given("the circle detector finds 5 friends with shared taste", target_fixture="ctx")
def _five():
    people = [mk(n) for n in ("ana", "ben", "cai", "dee", "eli")]
    for i, a in enumerate(people):
        for b in people[i + 1 :]:
            befriend(a, b)
    return {"people": people}


@when("it suggests the circle to one of them")
def _suggest(ctx, monkeypatch):
    from jingle_ml import tasks

    vec = np.array([1.0, 0.0])
    monkeypatch.setattr(tasks, "load_taste", lambda: ({str(p.pk): vec for p in ctx["people"]}, {}))
    assert tasks.suggest_circles()["created"] == 1
    s = SuggestedCircle.objects.get()
    ctx["suggestion"] = s
    owner = next(p for p in ctx["people"] if str(p.pk) == str(s.for_user_id))
    r = client(owner).post(
        f"/api/v1/circles/suggested/{s.pk}/create", {"name": "Indie night crew"}, format="json"
    )
    assert r.status_code == 201
    ctx["circle_id"], ctx["owner"] = r.json()["id"], owner


@then("no one is added until each person accepts an invite")
def _nobody_added(ctx):
    members = CircleMember.objects.filter(circle_id=ctx["circle_id"])
    assert [m.user_id for m in members] == [
        ctx["owner"].pk
    ]  # only the person who chose to create it
    invites = CircleInvite.objects.filter(circle_id=ctx["circle_id"])
    assert invites.count() == 4
    other = invites.first().invitee
    assert (
        client(other).post(f"/api/v1/circles/invites/{invites.first().pk}/accept").status_code
        == 200
    )
    assert CircleMember.objects.filter(circle_id=ctx["circle_id"]).count() == 2


# ---- rules --------------------------------------------------------------------------------


def test_JNG_04_01_create_and_limit_of_20(monkeypatch):
    a = mk("anna")
    c = client(a)
    r = c.post("/api/v1/circles", {"name": "College hip-hop crew"}, format="json")
    assert r.status_code == 201 and r.json()["my_role"] == "owner" and r.json()["member_count"] == 1
    assert c.post("/api/v1/circles", {"name": ""}, format="json").status_code == 400
    monkeypatch.setattr(services, "MAX_CIRCLES_PER_USER", 1)
    assert (
        c.post("/api/v1/circles", {"name": "Another"}, format="json").json()["error"]["code"]
        == "CIRCLE_LIMIT"
    )


def test_invites_only_friends_and_link_expiry():
    a, b, stranger = mk("anna"), mk("bala"), mk("str")
    befriend(a, b)
    circle = services.create_circle(a, "Crew")
    c = client(a)
    assert (
        c.post(
            f"/api/v1/circles/{circle.pk}/invites", {"user_ids": [str(stranger.pk)]}, format="json"
        ).status_code
        == 404
    )
    assert (
        c.post(
            f"/api/v1/circles/{circle.pk}/invites", {"user_ids": [str(b.pk)]}, format="json"
        ).status_code
        == 201
    )
    inv = client(b).get("/api/v1/circles/invites").json()
    assert inv[0]["circle"]["name"] == "Crew"
    token, link = services.create_link(circle, a)
    CircleInvite.objects.filter(pk=link.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
    assert APIClient().get(f"/api/v1/circles/join/{token}").status_code == 404  # 7-day expiry


def test_JNG_04_03_roles_and_JNG_04_06_leave_remove_transfer():
    o, adm, mem = mk("own"), mk("adm"), mk("mem")
    circle = services.create_circle(o, "Crew")
    token, _ = services.create_link(circle, o)
    for u in (adm, mem):
        services.join_by_link(token, u)
    co, ca, cm = client(o), client(adm), client(mem)
    base = f"/api/v1/circles/{circle.pk}"
    assert (
        ca.patch(f"{base}/members/{mem.pk}", {"role": "admin"}, format="json").status_code == 403
    )  # owner only
    assert co.patch(f"{base}/members/{adm.pk}", {"role": "admin"}, format="json").json() == {
        "role": "admin"
    }
    assert cm.delete(f"{base}/members/{adm.pk}").status_code == 403  # members can't remove
    assert (
        ca.patch(base, {"members_can_invite": False}, format="json").json()["members_can_invite"]
        is False
    )
    assert cm.post(f"{base}/links").status_code == 403  # JNG-04-07
    assert ca.delete(f"{base}/members/{mem.pk}").status_code == 204
    assert co.delete(base).json()["error"]["code"] == "OWNER_MUST_TRANSFER"
    assert co.post(f"{base}/transfer", {"user_id": str(adm.pk)}, format="json").status_code == 204
    assert CircleMember.objects.get(circle=circle, user=adm).role == Role.OWNER
    assert co.delete(base).status_code == 204  # now they can leave
    assert Circle.objects.get(pk=circle.pk).member_count == 1


def test_non_members_cannot_see_circle():
    o, x = mk("own"), mk("xxx")
    circle = services.create_circle(o, "Crew")
    assert client(x).get(f"/api/v1/circles/{circle.pk}").status_code == 404
    assert client(x).get(f"/api/v1/circles/{circle.pk}/feed").status_code == 404
    assert client(x).get("/api/v1/feed", {"circle": str(circle.pk)}).status_code == 404


def test_JNG_04_04_circle_feed_and_circles_visibility():
    o, m = mk("own"), mk("mem")
    circle = services.create_circle(o, "Crew")
    token, _ = services.create_link(circle, o)
    services.join_by_link(token, m)
    ps = PrivacySettings.for_user(m)
    ps.activity_visibility = ActivityVisibility.CIRCLES
    ps.save()
    assert policy.share_circle(o, m) and policy.can_view_activity(o, m)  # not friends, same circle
    feed = client(o).get(f"/api/v1/circles/{circle.pk}/feed").json()
    assert [c["friend"]["username"] for c in feed] == ["mem"]
    home = client(o).get("/api/v1/feed", {"circle": str(circle.pk)}).json()
    assert [c["friend"]["username"] for c in home["results"]] == ["mem"]  # JNG-05-03


def test_block_hides_member_in_circle():
    o, m = mk("own"), mk("mem")
    circle = services.create_circle(o, "Crew")
    token, _ = services.create_link(circle, o)
    services.join_by_link(token, m)
    social.block(o, m)
    names = [
        x["user"]["username"]
        for x in client(o).get(f"/api/v1/circles/{circle.pk}").json()["members"]
    ]
    assert names == ["own"]
    assert client(o).get(f"/api/v1/circles/{circle.pk}/feed").json() == []


def test_realtime_watch_list_includes_circle_co_members(settings):
    o, m = mk("own"), mk("mem")
    circle = services.create_circle(o, "Crew")
    token, _ = services.create_link(circle, o)
    services.join_by_link(token, m)
    r = APIClient().get(
        f"/internal/users/{o.pk}/friends", HTTP_X_SERVICE_TOKEN=settings.SERVICE_TOKEN
    )
    assert r.json() == [str(m.pk)]


def test_leiden_names_and_skips_existing():
    from jingle_ml.circles import jaccard, name_for, suggestions

    friends = {u: set() for u in "abcdefgh"}
    for grp in ("abcd", "efgh"):
        for x in grp:
            friends[x] |= set(grp) - {x}
    vecs = {u: np.array([1.0, 0.0]) for u in "abcd"} | {u: np.array([0.0, 1.0]) for u in "efgh"}
    out = suggestions(
        friends,
        vecs,
        existing=[set("efgh")],
        seeds={u: {"genres": ["Indie"]} for u in "abcd"},
        tops={},
    )
    assert [m for _, m, _ in out] == [list("abcd")]
    assert out[0][2] == "Your indie crew"
    assert jaccard(set("ab"), set("bc")) == pytest.approx(1 / 3)
    assert name_for(["a", "b"], {}, {}) == "Your crew"
