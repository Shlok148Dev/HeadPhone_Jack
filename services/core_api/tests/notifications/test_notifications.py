"""Notifications (EP-11: JNG-11-01…04, 07)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.services import create_account
from notifications import services
from notifications.models import Notification, NotificationPrefs, PushSubscription
from social import services as social

pytestmark = pytest.mark.django_db
IST = ZoneInfo("Asia/Kolkata")
NOON = datetime(2026, 10, 5, 12, tzinfo=IST)


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


@pytest.fixture
def pushes(monkeypatch):
    sent = []
    monkeypatch.setattr("notifications.tasks.push.delay", lambda nid: sent.append(nid))
    return sent


def subscribe(u):
    PushSubscription.objects.create(
        user=u, endpoint=f"https://push.example/{u.pk}", p256dh="k", auth="a"
    )


def test_JNG_11_01_in_app_centre_from_real_events(django_capture_on_commit_callbacks):
    a, b = mk("anna"), mk("bala")
    social.send_request(a, b)
    body = client(b).get("/api/v1/notifications").json()
    assert body["unread"] == 1
    assert body["results"][0]["title"] == "Anna wants to be friends"
    assert body["results"][0]["url"] == "/friends?tab=requests"
    assert client(b).post("/api/v1/notifications/read", {}, format="json").status_code == 204
    assert client(b).get("/api/v1/notifications").json()["unread"] == 0
    assert client(a).get("/api/v1/notifications").json()["results"] == []  # only mine


def test_JNG_11_02_push_only_after_opt_in(pushes, django_capture_on_commit_callbacks):
    u = mk("anna")
    with django_capture_on_commit_callbacks(execute=True):
        services.notify(u.pk, "send", "Hi", now=NOON)
    assert pushes == []  # no browser subscription: push is off by default
    subscribe(u)
    with django_capture_on_commit_callbacks(execute=True):
        services.notify(u.pk, "send", "Hi", now=NOON)
    assert len(pushes) == 1


def test_JNG_11_03_per_type_controls(pushes, django_capture_on_commit_callbacks):
    u = mk("anna")
    subscribe(u)
    c = client(u)
    s = c.get("/api/v1/me/notification-settings").json()
    assert s["types"]["battle"] == {"in_app": True, "push": True} and s["push_subscribed"]
    s["types"]["battle"] = {"in_app": True, "push": False}
    s["types"]["recap"] = {"in_app": False, "push": False}
    assert c.put("/api/v1/me/notification-settings", s, format="json").status_code == 200
    with django_capture_on_commit_callbacks(execute=True):
        services.notify(u.pk, "battle", "Results", now=NOON)
        services.notify(u.pk, "recap", "Recap", now=NOON)
    assert Notification.objects.filter(user=u).values_list("type", flat=True).get() == "battle"
    assert pushes == []
    bad = {**s, "quiet_start": "25:00"}
    assert c.put("/api/v1/me/notification-settings", bad, format="json").status_code == 400


def test_JNG_11_04_quiet_hours_span_midnight():
    p = NotificationPrefs(quiet_start="23:00", quiet_end="08:00", tz="Asia/Kolkata")
    assert services.in_quiet_hours(p, datetime(2026, 10, 5, 23, 30, tzinfo=IST))
    assert services.in_quiet_hours(p, datetime(2026, 10, 5, 7, 59, tzinfo=IST))
    assert not services.in_quiet_hours(p, NOON)
    p.tz = "Europe/London"  # 12:00 IST is 07:30 in London: still quiet there
    assert services.in_quiet_hours(p, NOON)


def test_quiet_hours_keep_in_app_but_skip_push(pushes, django_capture_on_commit_callbacks):
    u = mk("anna")
    subscribe(u)
    with django_capture_on_commit_callbacks(execute=True):
        n = services.notify(u.pk, "send", "Late", now=datetime(2026, 10, 5, 23, 30, tzinfo=IST))
    assert n is not None and pushes == []


def test_JNG_11_07_five_pushes_a_day(pushes, django_capture_on_commit_callbacks):
    u = mk("anna")
    subscribe(u)
    with django_capture_on_commit_callbacks(execute=True):
        for i in range(7):
            services.notify(u.pk, "send", f"n{i}", now=NOON)
    assert len(pushes) == 5
    assert Notification.objects.filter(user=u).count() == 7  # in-app still gets everything


def test_push_subscription_needs_vapid_and_https(settings):
    u = mk("anna")
    c = client(u)
    body = {"endpoint": "https://push.example/x", "keys": {"p256dh": "k", "auth": "a"}}
    settings.VAPID_PUBLIC_KEY = ""
    assert c.post("/api/v1/me/push-subscription", body, format="json").status_code == 400
    settings.VAPID_PUBLIC_KEY = "pub"
    assert c.get("/api/v1/notifications/push-key").json() == {
        "available": True,
        "public_key": "pub",
    }
    assert (
        c.post(
            "/api/v1/me/push-subscription", {**body, "endpoint": "http://x"}, format="json"
        ).status_code
        == 400
    )
    assert c.post("/api/v1/me/push-subscription", body, format="json").status_code == 204
    assert c.delete("/api/v1/me/push-subscription").status_code == 204
    assert not PushSubscription.objects.exists()


def test_send_push_drops_gone_subscriptions(monkeypatch, settings):
    import pywebpush

    u = mk("anna")
    subscribe(u)
    settings.VAPID_PRIVATE_KEY = "priv"
    n = Notification.objects.create(user=u, type="send", title="Hi")

    class Gone(pywebpush.WebPushException):
        def __init__(self):
            super().__init__("gone")
            self.response = type("R", (), {"status_code": 410})()

    def boom(**kw):
        raise Gone()

    monkeypatch.setattr(pywebpush, "webpush", boom)
    assert services.send_push(str(n.pk)) == 0
    assert not PushSubscription.objects.exists()
    calls = []
    subscribe(u)
    monkeypatch.setattr(pywebpush, "webpush", lambda **kw: calls.append(kw))
    assert services.send_push(str(n.pk)) == 1 and calls[0]["vapid_claims"]["sub"]
