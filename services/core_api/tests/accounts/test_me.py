"""/api/v1/me, /me/privacy (JNG-02-05, JNG-02-06), /me/consents (NFR-PRIV-01)."""

import json
from datetime import date, timedelta

import pytest
import time_machine
from django.utils import timezone
from rest_framework.test import APIClient

from accounts import services
from accounts.models import Consent, User
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestMe:
    def test_unauthenticated(self, api):
        r = api.get("/api/v1/me")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "UNAUTHENTICATED"

    def test_get(self, auth_api, user):
        r = auth_api.get("/api/v1/me")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == str(user.pk)
        assert "birth_year" not in body and "google_sub" not in body and "password" not in body
        assert body["private_mode"] == {"active": False, "until": None}
        assert r["Cache-Control"] == "private, no-store"

    def test_patch_profile(self, auth_api, user):
        r = auth_api.patch(
            "/api/v1/me",
            {"display_name": "  Asha K ", "college": "IIT Delhi", "city": "Delhi",
             "username": "Asha.New"},
            format="json",
        )
        assert r.status_code == 200, r.content
        user.refresh_from_db()
        assert (user.display_name, user.college, user.city, user.username) == (
            "Asha K", "IIT Delhi", "Delhi", "asha.new")

    def test_patch_username_taken_case_insensitive(self, auth_api):
        UserFactory(username="taken")
        r = auth_api.patch("/api/v1/me", {"username": "TAKEN"}, format="json")
        assert r.status_code == 400
        assert "username" in r.json()["error"]["details"]

    def test_patch_same_username_ok(self, auth_api, user):
        r = auth_api.patch("/api/v1/me", {"username": user.username.upper()}, format="json")
        assert r.status_code == 200

    def test_patch_profanity(self, auth_api):
        r = auth_api.patch("/api/v1/me", {"city": "shit town"}, format="json")
        assert r.status_code == 400

    def test_birth_year_locked_once_set(self, auth_api):
        r = auth_api.patch("/api/v1/me", {"birth_year": 1990}, format="json")
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "BIRTH_YEAR_LOCKED"

    def test_onboarding_sets_birth_year(self, db):
        user = UserFactory(birth_year=None)
        client = APIClient()
        client.force_authenticate(user)
        assert client.get("/api/v1/me").json()["needs_onboarding"] is True
        assert client.get("/api/v1/me/card").json()["error"]["code"] == "ONBOARDING_REQUIRED"
        r = client.patch("/api/v1/me", {"birth_year": 2000}, format="json")
        assert r.status_code == 200
        assert r.json()["needs_onboarding"] is False
        assert client.get("/api/v1/me/card").status_code == 200

    def test_onboarding_under_18_removes_account(self, db):
        user = UserFactory(birth_year=None)
        client = APIClient()
        client.force_authenticate(user)
        r = client.patch("/api/v1/me", {"birth_year": date.today().year - 16}, format="json")
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "AGE_RESTRICTED"
        assert not User.objects.filter(pk=user.pk).exists()

    def test_empty_patch(self, auth_api):
        assert auth_api.patch("/api/v1/me", {}, format="json").status_code == 200


class TestPrivacy:
    def test_get_defaults(self, auth_api):
        r = auth_api.get("/api/v1/me/privacy")
        assert r.status_code == 200
        assert r.json() == {
            "activity_visibility": "friends",
            "show_last_active": True,
            "concerts_visible": False,
            "private_mode": {"active": False, "until": None},
        }

    def test_unauthenticated(self, api):
        assert api.get("/api/v1/me/privacy").status_code == 401

    def test_patch_settings_publishes_invalidate(self, auth_api, user, fake_redis):
        r = auth_api.patch(
            "/api/v1/me/privacy",
            {"activity_visibility": "nobody", "show_last_active": False},
            format="json",
        )
        assert r.status_code == 200
        assert r.json()["activity_visibility"] == "nobody"
        assert r.json()["show_last_active"] is False
        entries = fake_redis.xrange("events:domain")
        assert entries[-1][1]["type"] == "feed.invalidate"
        assert json.loads(entries[-1][1]["data"]) == {"user_id": str(user.pk)}

    def test_invalid_visibility(self, auth_api):
        r = auth_api.patch("/api/v1/me/privacy", {"activity_visibility": "world"}, format="json")
        assert r.status_code == 400

    @pytest.mark.parametrize("choice,hours", [("1h", 1), ("8h", 8)])
    def test_private_mode_timed(self, auth_api, user, choice, hours):
        with time_machine.travel("2026-09-29T10:00:00Z", tick=False):
            r = auth_api.patch("/api/v1/me/privacy", {"private_mode": choice}, format="json")
            assert r.json()["private_mode"]["active"] is True
            assert r.json()["private_mode"]["until"] == f"2026-09-29T{10 + hours:02d}:00:00Z" or \
                r.json()["private_mode"]["until"].startswith("2026-09-29")
        user.refresh_from_db()
        assert user.private_until == timezone.datetime(
            2026, 9, 29, 10 + hours, tzinfo=timezone.get_fixed_timezone(0))
        with time_machine.travel(f"2026-09-29T{10 + hours:02d}:00:01Z", tick=False):
            user.refresh_from_db()
            assert services.private_mode_state(user)["active"] is False

    def test_private_mode_until_off_then_off(self, auth_api, user):
        r = auth_api.patch("/api/v1/me/privacy", {"private_mode": "until_off"}, format="json")
        assert r.json()["private_mode"] == {"active": True, "until": None}
        r = auth_api.patch("/api/v1/me/privacy", {"private_mode": "off"}, format="json")
        assert r.json()["private_mode"] == {"active": False, "until": None}
        user.refresh_from_db()
        assert user.private_until is None

    def test_invalid_private_mode(self, auth_api):
        r = auth_api.patch("/api/v1/me/privacy", {"private_mode": "3h"}, format="json")
        assert r.status_code == 400

    def test_privacy_row_created_lazily(self, db):
        user = User.objects.create_user(username="lazy", email="lazy@example.test", password="x")
        client = APIClient()
        client.force_authenticate(user)
        assert client.get("/api/v1/me/privacy").status_code == 200


class TestConsents:
    def _register(self, api):
        from tests.accounts.test_auth import register_payload

        r = api.post("/api/v1/auth/register", register_payload(), format="json")
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
        return User.objects.get(pk=r.json()["user"]["id"])

    def test_list_itemised(self, api):
        self._register(api)
        r = api.get("/api/v1/me/consents")
        assert r.status_code == 200
        items = {i["purpose"]: i for i in r.json()}
        assert set(items) == {
            "core_service", "activity_sharing", "suggestions_discoverability",
            "contact_matching", "push_notifications", "email_digest", "lastfm_link",
        }
        assert items["core_service"]["given"] is True
        assert items["core_service"]["required"] is True
        assert items["core_service"]["version"] == "2026-09"
        assert items["email_digest"]["given"] is False
        assert all(i["description"] for i in items.values())

    def test_give_and_withdraw(self, api):
        user = self._register(api)
        r = api.post("/api/v1/me/consents/email_digest", {"given": True}, format="json")
        assert r.status_code == 200 and r.json()["given"] is True
        # idempotent grant
        api.post("/api/v1/me/consents/email_digest", {"given": True}, format="json")
        assert Consent.objects.filter(user=user, purpose="email_digest").count() == 1
        r = api.post("/api/v1/me/consents/email_digest", {"given": False}, format="json")
        assert r.json()["given"] is False and r.json()["withdrawn_at"]
        r = api.post("/api/v1/me/consents/email_digest", {"given": True}, format="json")
        assert r.json()["given"] is True
        assert Consent.objects.filter(user=user, purpose="email_digest").count() == 2

    def test_discoverability_consent_toggles_discoverable(self, api):
        user = self._register(api)
        api.post("/api/v1/me/consents/suggestions_discoverability", {"given": True}, format="json")
        user.refresh_from_db()
        assert user.discoverable is True
        api.post("/api/v1/me/consents/suggestions_discoverability", {"given": False},
                 format="json")
        user.refresh_from_db()
        assert user.discoverable is False

    def test_withdraw_core_service_refused(self, api):
        self._register(api)
        r = api.post("/api/v1/me/consents/core_service", {"given": False}, format="json")
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "CONSENT_REQUIRED"

    def test_unknown_purpose(self, auth_api):
        r = auth_api.post("/api/v1/me/consents/marketing", {"given": True}, format="json")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "UNKNOWN_PURPOSE"

    def test_bad_body(self, auth_api):
        r = auth_api.post("/api/v1/me/consents/email_digest", {}, format="json")
        assert r.status_code == 400

    def test_unauthenticated(self, api):
        assert api.get("/api/v1/me/consents").status_code == 401
        assert api.post("/api/v1/me/consents/email_digest", {"given": True}).status_code == 401

    def test_withdraw_when_never_given_is_noop(self, auth_api):
        r = auth_api.post("/api/v1/me/consents/push_notifications", {"given": False},
                          format="json")
        assert r.status_code == 200 and r.json()["given"] is False


def test_private_mode_state_expired(db):
    user = UserFactory(private_until=timezone.now() - timedelta(minutes=1))
    assert services.private_mode_state(user) == {"active": False, "until": None}
