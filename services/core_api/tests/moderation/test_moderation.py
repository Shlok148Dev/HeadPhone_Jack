"""Moderation console and admin (EP-12: JNG-12-01…06, 08)."""

import httpx
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.services import create_account
from circles import services as circles
from core_api.models import FeatureFlag
from moderation.models import AuditEntry, ModerationAction
from sends import services as sends
from social import services as social
from social.models import Report

pytestmark = pytest.mark.django_db


def mk(name, staff=False):
    u = create_account(
        email=f"{name}@x.test",
        username=name,
        password="password-1234",
        display_name=name.title(),
        birth_year=1999,
    )
    if staff:
        u.is_staff = True
        u.save(update_fields=["is_staff"])
    return u


def client(u):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(u)}")
    return c


def befriend(a, b):
    social.accept(b, social.send_request(a, b))


def report(by, kind, target_id, reason="harassment"):
    r = client(by).post(
        "/api/v1/reports",
        {"target_type": kind, "target_id": str(target_id), "reason": reason, "details": "not ok"},
        format="json",
    )
    assert r.status_code == 201, r.json()
    return Report.objects.latest("created_at")


def test_JNG_12_01_report_circles_and_notes_only_if_you_can_see_them():
    a, b, x = mk("anna"), mk("bala"), mk("xavi")
    befriend(a, b)
    c = circles.create_circle(b, "Bad name")
    token, _ = circles.create_link(c, b)
    circles.join_by_link(token, a)
    report(a, "circle", c.pk)
    rec = sends.send(b, [{"title": "Song", "artist": "X"}], note="rude note", user_ids=[str(a.pk)])
    report(a, "send", rec.deliveries.get().pk)
    assert (
        client(x)
        .post(
            "/api/v1/reports",
            {"target_type": "circle", "target_id": str(c.pk), "reason": "spam"},
            format="json",
        )
        .status_code
        == 404
    )


def test_JNG_12_02_queue_is_staff_only_with_context():
    a, b, mod = mk("anna"), mk("bala"), mk("mod", staff=True)
    befriend(a, b)
    rec = sends.send(b, [{"title": "Song", "artist": "X"}], note="rude note", user_ids=[str(a.pk)])
    report(a, "send", rec.deliveries.get().pk)
    assert client(a).get("/api/v1/mod/reports").status_code == 403
    row = client(mod).get("/api/v1/mod/reports").json()["results"][0]
    assert row["content"] == "Note: “rude note”" and row["responsible"]["username"] == "bala"
    assert row["reporter"] == "anna" and row["past_actions"] == 0


def test_JNG_12_03_mute_blocks_posting_and_is_audited():
    a, b, mod = mk("anna"), mk("bala"), mk("mod", staff=True)
    befriend(a, b)
    r = report(a, "user", b.pk)
    resp = client(mod).post(
        f"/api/v1/mod/reports/{r.pk}/action",
        {"kind": "mute", "reason": "Harassing notes", "days": 3},
        format="json",
    )
    assert resp.status_code == 204
    r.refresh_from_db()
    assert r.status == "actioned"
    blocked = client(b).post(
        "/api/v1/recommendations",
        {"items": [{"title": "x", "artist": "y"}], "user_ids": [str(a.pk)]},
        format="json",
    )
    assert blocked.status_code == 403 and blocked.json()["error"]["code"] == "MUTED"
    assert client(b).get("/api/v1/feed").status_code == 200  # muted, not locked out
    assert AuditEntry.objects.filter(action="moderation.mute").exists()
    assert client(mod).get("/api/v1/mod/audit").json()["results"][0]["actor"] == "mod"
    assert client(b).get("/api/v1/notifications").json()["results"][0]["type"] == "moderation"


def test_suspend_locks_the_app_but_not_appeals_and_ban_deactivates():
    a, b, mod = mk("anna"), mk("bala"), mk("mod", staff=True)
    r = report(a, "user", b.pk)
    client(mod).post(
        f"/api/v1/mod/reports/{r.pk}/action",
        {"kind": "suspend", "reason": "Spam", "days": 1},
        format="json",
    )
    cb = client(b)
    assert cb.get("/api/v1/feed").json()["error"]["code"] == "SUSPENDED"
    assert cb.get("/api/v1/friends").status_code == 403
    mine = cb.get("/api/v1/me/moderation").json()["actions"]
    assert mine[0]["kind"] == "suspend"
    assert (
        cb.post(
            f"/api/v1/me/moderation/{mine[0]['id']}/appeal",
            {"text": "It was a mistake"},
            format="json",
        ).status_code
        == 201
    )
    r2 = report(a, "user", b.pk, "spam")
    client(mod).post(
        f"/api/v1/mod/reports/{r2.pk}/action",
        {"kind": "ban", "reason": "Repeated spam"},
        format="json",
    )
    b.refresh_from_db()
    assert b.is_active is False
    assert (
        client(mod)
        .post(f"/api/v1/mod/reports/{r2.pk}/action", {"kind": "warn", "reason": "x"}, format="json")
        .status_code
        == 404
    )


def test_JNG_12_08_overturned_appeal_lifts_the_action():
    a, b, mod = mk("anna"), mk("bala"), mk("mod", staff=True)
    r = report(a, "user", b.pk)
    client(mod).post(
        f"/api/v1/mod/reports/{r.pk}/action", {"kind": "mute", "reason": "Mistake"}, format="json"
    )
    action = ModerationAction.objects.get()
    client(b).post(
        f"/api/v1/me/moderation/{action.pk}/appeal", {"text": "Wrong person"}, format="json"
    )
    assert (
        client(b)
        .post(f"/api/v1/me/moderation/{action.pk}/appeal", {"text": "again"}, format="json")
        .status_code
        == 409
    )
    queue = client(mod).get("/api/v1/mod/appeals").json()["results"]
    assert queue[0]["text"] == "Wrong person"
    assert (
        client(mod)
        .post(
            f"/api/v1/mod/appeals/{queue[0]['id']}/decide",
            {"overturn": True, "note": "Sorry"},
            format="json",
        )
        .status_code
        == 204
    )
    ok = client(b).post(
        "/api/v1/recommendations",
        {"items": [{"title": "x", "artist": "y"}], "user_ids": [str(a.pk)]},
        format="json",
    )
    assert ok.json()["error"]["code"] != "MUTED"  # not muted any more (404: not friends)
    assert (
        client(b).get("/api/v1/me/moderation").json()["actions"][0]["appeal"]["status"]
        == "overturned"
    )


def test_moderators_need_a_reason_and_cannot_act_on_themselves():
    a, mod = mk("anna"), mk("mod", staff=True)
    r = report(a, "user", mod.pk)
    assert (
        client(mod)
        .post(f"/api/v1/mod/reports/{r.pk}/action", {"kind": "warn", "reason": "x"}, format="json")
        .status_code
        == 403
    )
    r2 = report(mod, "user", a.pk)
    assert (
        client(mod)
        .post(f"/api/v1/mod/reports/{r2.pk}/action", {"kind": "warn", "reason": " "}, format="json")
        .status_code
        == 400
    )
    assert (
        client(mod)
        .post(f"/api/v1/mod/reports/{r2.pk}/action", {"kind": "dismiss"}, format="json")
        .status_code
        == 204
    )


def test_JNG_12_05_flags_toggle_is_audited():
    mod = mk("mod", staff=True)
    name = FeatureFlag.objects.values_list("name", flat=True).first()
    c = client(mod)
    before = next(f for f in c.get("/api/v1/admin/flags").json()["results"] if f["name"] == name)[
        "enabled"
    ]
    assert (
        c.put(
            "/api/v1/admin/flags", {"name": name, "enabled": not before}, format="json"
        ).status_code
        == 204
    )
    assert FeatureFlag.objects.get(name=name).enabled is (not before)
    assert AuditEntry.objects.filter(action="flag.set", target=f"flag:{name}").exists()
    assert (
        client(mk("anna"))
        .put("/api/v1/admin/flags", {"name": name, "enabled": True}, format="json")
        .status_code
        == 403
    )


def test_JNG_12_06_spotify_allowlist_max_5_and_used_by_connect(settings):
    from sources.connect_views import _allowlisted

    mod = mk("mod", staff=True)
    tester = mk("tester")
    settings.SPOTIFY_ALLOWLIST = ""
    c = client(mod)
    assert not _allowlisted(tester)
    assert (
        c.post("/api/v1/admin/allowlist", {"email": "tester@x.test"}, format="json").status_code
        == 204
    )
    assert _allowlisted(tester)
    for i in range(4):
        c.post("/api/v1/admin/allowlist", {"email": f"t{i}@x.test"}, format="json")
    assert (
        c.post("/api/v1/admin/allowlist", {"email": "six@x.test"}, format="json").json()["error"][
            "code"
        ]
        == "ALLOWLIST_FULL"
    )
    assert (
        c.delete("/api/v1/admin/allowlist", {"email": "tester@x.test"}, format="json").status_code
        == 204
    )
    assert not _allowlisted(tester)
    assert len(c.get("/api/v1/admin/allowlist").json()["emails"]) == 4


def test_JNG_12_04_budgets_proxy_ingest(monkeypatch):
    mod = mk("mod", staff=True)
    body = {
        "sources": [
            {
                "source": "lastfm",
                "capacity": 4,
                "per_second": 4.0,
                "used_last_minute": 3,
                "used_last_hour": 90,
                "rejected_last_hour": 0,
            }
        ]
    }

    class R:
        def raise_for_status(self):
            return None

        def json(self):
            return body

    monkeypatch.setattr(httpx, "get", lambda *a, **k: R())
    got = client(mod).get("/api/v1/admin/budgets").json()
    assert got["available"] and got["sources"][0]["used_last_hour"] == 90

    def down(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "get", down)
    assert client(mod).get("/api/v1/admin/budgets").json() == {"available": False, "sources": []}
