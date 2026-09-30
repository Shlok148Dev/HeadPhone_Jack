"""EP-02 social graph + JNG-12-01 reports. Gherkin: tests/features/ep02/JNG-02-03_04_remove_block.feature."""

import pytest
from pytest_bdd import given, scenarios, then, when
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import ActivityVisibility, PrivacySettings
from accounts.services import create_account
from core_api import policy
from social import services
from social.models import Block, Friendship, FriendshipStatus, Report

pytestmark = pytest.mark.django_db
scenarios("../features/ep02/JNG-02-03_04_remove_block.feature")


def mk(name: str, discoverable: bool = True):
    u = create_account(
        email=f"{name}@x.test",
        username=name,
        password="password-1234",
        display_name=name.title(),
        birth_year=1999,
    )
    u.discoverable = discoverable
    u.save(update_fields=["discoverable"])
    return u


def client_for(user) -> APIClient:
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return c


def befriend(a, b):
    f = services.send_request(a, b)
    return services.accept(b, f)


# ---- Gherkin (JNG-02-03, JNG-02-04) --------------------------------------------------------


@pytest.fixture
def ctx():
    return {}


@given("Asha and Ravi are friends", target_fixture="ctx")
def _friends():
    asha, ravi = mk("asha"), mk("ravi")
    befriend(asha, ravi)
    return {"asha": asha, "ravi": ravi}


@when("Asha blocks Ravi")
def _block(ctx):
    r = client_for(ctx["asha"]).post(
        "/api/v1/blocks", {"user_id": str(ctx["ravi"].pk)}, format="json"
    )
    assert r.status_code == 201


@then("neither sees the other in feed, search, friends or requests")
def _hidden(ctx):
    asha, ravi = ctx["asha"], ctx["ravi"]
    assert not policy.can_view_activity(asha, ravi) and not policy.can_view_activity(ravi, asha)
    for me, other in ((asha, ravi), (ravi, asha)):
        c = client_for(me)
        assert c.get("/api/v1/friends").json() == []
        assert c.get("/api/v1/friends/requests").json() == []
        assert c.get("/api/v1/users/search", {"q": other.username}).json() == []
    # Sending a request to a blocker looks exactly like "no such user".
    r = client_for(ravi).post("/api/v1/friends/requests", {"user_id": str(asha.pk)}, format="json")
    assert r.status_code == 404


@then("Ravi receives no notification of the block")
def _no_notice(ctx, monkeypatch):
    sent = []
    monkeypatch.setattr("core_api.events.publish_domain", lambda t, p: sent.append((t, p)))
    services.block(ctx["asha"], ctx["ravi"])
    assert all(t != "notify" for t, _ in sent)


@given("Ravi has a pending request to Asha", target_fixture="ctx")
def _pending():
    asha, ravi = mk("asha"), mk("ravi")
    client_for(ravi).post("/api/v1/friends/requests", {"username": "asha"}, format="json")
    return {"asha": asha, "ravi": ravi}


@when("Asha sends a request to Ravi")
def _cross(ctx):
    r = client_for(ctx["asha"]).post(
        "/api/v1/friends/requests", {"user_id": str(ctx["ravi"].pk)}, format="json"
    )
    assert r.status_code == 201 and r.json()["relationship"] == "friends"


@then("both requests resolve into one accepted friendship")
def _one(ctx):
    rows = Friendship.objects.all()
    assert rows.count() == 1 and rows[0].status == FriendshipStatus.ACCEPTED


# ---- Requests lifecycle (JNG-02-02) --------------------------------------------------------


def test_request_accept_decline_cancel():
    a, b, c = mk("anna"), mk("bala"), mk("chir")
    ca, cb = client_for(a), client_for(b)
    ca.post("/api/v1/friends/requests", {"username": "@bala"}, format="json")
    incoming = cb.get("/api/v1/friends/requests").json()
    assert [(r["direction"], r["user"]["username"]) for r in incoming] == [("incoming", "anna")]
    assert ca.get("/api/v1/friends/requests").json()[0]["direction"] == "outgoing"
    rid = incoming[0]["id"]
    assert (
        ca.post(f"/api/v1/friends/requests/{rid}/accept").status_code == 404
    )  # only the recipient
    assert cb.post(f"/api/v1/friends/requests/{rid}/accept").json() == {"status": "accepted"}
    assert [f["username"] for f in ca.get("/api/v1/friends").json()] == ["bala"]
    assert policy.are_friends(a, b) and policy.can_view_activity(a, b)
    # decline and cancel
    f = services.send_request(c, a)
    assert ca.post(f"/api/v1/friends/requests/{f.pk}/decline").status_code == 204
    f = services.send_request(c, a)
    assert client_for(c).delete(f"/api/v1/friends/requests/{f.pk}").status_code == 204
    assert not Friendship.objects.filter(pk=f.pk).exists()


def test_cannot_add_self_or_unknown():
    a = mk("anna")
    c = client_for(a)
    assert (
        c.post("/api/v1/friends/requests", {"user_id": str(a.pk)}, format="json").status_code == 400
    )
    assert (
        c.post("/api/v1/friends/requests", {"username": "ghost"}, format="json").status_code == 404
    )


def test_daily_request_limit(monkeypatch):
    a = mk("anna")
    monkeypatch.setattr(services, "DAILY_REQUEST_LIMIT", 2)
    services.send_request(a, mk("u1"))
    services.send_request(a, mk("u2"))
    with pytest.raises(Exception) as err:
        services.send_request(a, mk("u3"))
    assert getattr(err.value, "code", "") == "RATE_LIMITED"


def test_JNG_02_03_remove_friend_hides_activity_at_once():
    a, b = mk("anna"), mk("bala")
    befriend(a, b)
    assert policy.can_view_activity(b, a)
    assert client_for(a).delete(f"/api/v1/friends/{b.pk}").status_code == 204
    assert not policy.can_view_activity(b, a)
    assert client_for(a).delete(f"/api/v1/friends/{b.pk}").status_code == 404


def test_privacy_visibility_rules():
    a, b = mk("anna"), mk("bala")
    befriend(a, b)
    ps = PrivacySettings.for_user(a)
    ps.activity_visibility = ActivityVisibility.CIRCLES
    ps.save()
    assert not policy.can_view_activity(b, a)  # friends alone aren't enough with "circles"
    ps.activity_visibility = ActivityVisibility.NOBODY
    ps.save()
    assert not policy.can_view_activity(b, a)
    assert policy.can_view_activity(a, a)


def test_search_rules():
    a, b, hidden = mk("anna"), mk("bala"), mk("shy", discoverable=False)
    hidden.display_name = "Bashful"
    hidden.save(update_fields=["display_name"])
    c = client_for(a)
    assert [u["username"] for u in c.get("/api/v1/users/search", {"q": "ba"}).json()] == ["bala"]
    assert (
        c.get("/api/v1/users/search", {"q": "shy"}).json()[0]["username"] == "shy"
    )  # username still works
    assert (
        c.get("/api/v1/users/search", {"q": "Bashful"}).json() == []
    )  # display name needs discoverable
    assert c.get("/api/v1/users/search", {"q": "a"}).json() == []  # too short
    assert c.get("/api/v1/users/search", {"q": "anna"}).json() == []  # never yourself
    services.send_request(a, b)
    assert c.get("/api/v1/users/search", {"q": "bala"}).json()[0]["relationship"] == "outgoing"


def test_blocks_list_and_unblock():
    a, b = mk("anna"), mk("bala")
    c = client_for(a)
    c.post("/api/v1/blocks", {"user_id": str(b.pk)}, format="json")
    assert [u["username"] for u in c.get("/api/v1/blocks").json()] == ["bala"]
    assert c.delete(f"/api/v1/blocks/{b.pk}").status_code == 204
    assert not Block.objects.exists()


def test_JNG_12_01_report_user():
    a, b = mk("anna"), mk("bala")
    c = client_for(a)
    assert (
        c.post(
            "/api/v1/reports",
            {"target_type": "user", "target_id": str(b.pk), "reason": "nope"},
            format="json",
        ).status_code
        == 400
    )
    r = c.post(
        "/api/v1/reports",
        {"target_type": "user", "target_id": str(b.pk), "reason": "spam", "details": "x" * 2000},
        format="json",
    )
    assert r.status_code == 201
    rep = Report.objects.get()
    assert rep.reporter == a and len(rep.details) == 1000


def test_JNG_02_07_invite_link_auto_sends_request():
    a, b = mk("anna"), mk("bala")
    inv = client_for(a).get("/api/v1/me/invite").json()
    assert inv["url"].endswith(f"/invite/{inv['code']}") and inv["qr_svg"].startswith("<?xml")
    assert APIClient().get(f"/api/v1/invites/{inv['code']}").json() == {"display_name": "Anna"}
    assert APIClient().post(f"/api/v1/invites/{inv['code']}").status_code == 401
    r = client_for(b).post(f"/api/v1/invites/{inv['code']}")
    assert r.status_code == 201 and r.json()["relationship"] == "outgoing"
    new = client_for(a).post("/api/v1/me/invite").json()  # rotate: old link dies
    assert new["code"] != inv["code"]
    assert APIClient().get(f"/api/v1/invites/{inv['code']}").status_code == 404


def test_internal_friend_ids(settings):
    a, b = mk("anna"), mk("bala")
    befriend(a, b)
    c = APIClient()
    r = c.get(f"/internal/users/{a.pk}/friends", HTTP_X_SERVICE_TOKEN=settings.SERVICE_TOKEN)
    assert r.json() == [str(b.pk)]
