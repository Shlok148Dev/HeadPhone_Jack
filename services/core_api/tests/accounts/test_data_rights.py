"""JNG-01-10 account deletion, JNG-13-04 export."""

import json
from datetime import UTC, datetime, timedelta
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from accounts import services, tasks
from accounts.models import Consent, PrivacySettings, User
from sources.models import LinkedSource, PlatformConnection, ScrobbleToken
from tests.factories import PASSWORD, UserFactory, put_signal

pytestmark = pytest.mark.django_db


def _login(api, email):
    r = api.post("/api/v1/auth/login", {"email": email, "password": PASSWORD}, format="json")
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    return r


def _seed_sources(user):
    PlatformConnection.objects.create(user=user, platform="SPOTIFY", status="CONNECTED")
    LinkedSource.objects.create(user=user, kind="SPOTIFY", token_ciphertext="enc")
    LinkedSource.objects.create(user=user, kind="LISTENBRAINZ", token_ciphertext="enc")
    ScrobbleToken.objects.create(user=user, token_sha256=user.pk.hex * 2)


class TestDeleteAccount:
    def test_soft_delete_anonymises_revokes_and_enqueues(
        self, api, fake_redis, mongo_db, django_capture_on_commit_callbacks
    ):
        user = UserFactory(email="del@example.test", college="IIT", city="Pune")
        _seed_sources(user)
        services.give_consent(user, "email_digest")
        put_signal(fake_redis, "np", user.pk, observed_at=1)
        put_signal(fake_redis, "last", user.pk, observed_at=1)
        uid = str(user.pk)
        mongo_db.listens.insert_many(
            [
                {
                    "user_id": uid,
                    "via": "DIRECT",
                    "platform": "SPOTIFY",
                    "played_at": datetime.now(UTC),
                },
                {
                    "user_id": uid,
                    "via": "COMPANION",
                    "platform": "SPOTIFY",
                    "played_at": datetime.now(UTC),
                },
            ]
        )
        _login(api, "del@example.test")
        with (
            mock.patch.object(tasks.purge_user, "apply_async") as enqueue,
            django_capture_on_commit_callbacks(execute=True),
        ):
            r = api.delete("/api/v1/me", {"password": PASSWORD}, format="json")
        assert r.status_code == 202, r.content
        assert r.json()["purge_within_days"] == 30
        assert r.cookies["jingle_refresh"].value == ""
        enqueue.assert_called_once()
        assert enqueue.call_args.kwargs["args"] == [uid]
        assert enqueue.call_args.kwargs["countdown"] == 30 * 86400

        user.refresh_from_db()
        assert user.deleted_at is not None and not user.is_active
        assert user.email.endswith("@deleted.invalid")
        assert user.username.startswith("del_") and len(user.username) <= 20
        assert (user.display_name, user.college, user.city, user.birth_year) == ("", "", "", None)
        assert not user.has_usable_password()
        assert not Consent.objects.filter(user=user, withdrawn_at__isnull=True).exists()
        # tokens revoked
        assert (
            OutstandingToken.objects.filter(user=user).count()
            == BlacklistedToken.objects.filter(token__user=user).count()
            > 0
        )
        # Spotify-direct data removed immediately (BR-03); other routes wait for the purge
        assert not LinkedSource.objects.filter(user=user, kind="SPOTIFY").exists()
        assert LinkedSource.objects.filter(user=user, kind="LISTENBRAINZ").exists()
        assert mongo_db.listens.count_documents({"user_id": uid}) == 1
        # live state gone; domain event published
        assert not fake_redis.exists(f"np:{uid}", f"last:{uid}")
        assert fake_redis.xrange("events:domain")[-1][1]["type"] == "feed.invalidate"
        # access token no longer works (user inactive)
        assert api.get("/api/v1/me").status_code == 401
        # refresh no longer works
        assert (
            APIClient()
            .post(
                "/api/v1/auth/login",
                {"email": "del@example.test", "password": PASSWORD},
                format="json",
            )
            .status_code
            == 401
        )

    def test_requires_password(self, auth_api):
        r = auth_api.delete("/api/v1/me", {}, format="json")
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "CONFIRMATION_REQUIRED"

    def test_wrong_password(self, auth_api):
        r = auth_api.delete("/api/v1/me", {"password": "wrong-one"}, format="json")
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "CONFIRMATION_FAILED"

    def test_google_only_account_confirms_with_username(self, db):
        user = UserFactory(username="meera")
        user.set_unusable_password()
        user.save()
        client = APIClient()
        client.force_authenticate(user)
        assert client.delete("/api/v1/me", {"confirm": "nope"}, format="json").status_code == 400
        with mock.patch.object(tasks.purge_user, "apply_async"):
            r = client.delete("/api/v1/me", {"confirm": "Meera"}, format="json")
        assert r.status_code == 202

    def test_unauthenticated(self, api):
        assert api.delete("/api/v1/me").status_code == 401

    def test_enqueue_failure_is_tolerated(self, auth_api, django_capture_on_commit_callbacks):
        with (
            mock.patch.object(tasks.purge_user, "apply_async", side_effect=RuntimeError),
            django_capture_on_commit_callbacks(execute=True),
        ):
            r = auth_api.delete("/api/v1/me", {"password": PASSWORD}, format="json")
        assert r.status_code == 202


class TestPurge:
    def _deleted_user(self, mongo_db, days_ago=31):
        user = UserFactory()
        _seed_sources(user)
        mongo_db.listens.insert_one({"meta": {"user_id": str(user.pk)}, "played_at": 1})
        mongo_db.listens.insert_one({"user_id": "someone-else", "played_at": 1})
        services.soft_delete_account(user)
        User.objects.filter(pk=user.pk).update(deleted_at=timezone.now() - timedelta(days=days_ago))
        return user

    def test_purge_user_after_30_days(self, mongo_db):
        user = self._deleted_user(mongo_db)
        assert tasks.purge_user.run(str(user.pk)) is True
        assert not User.objects.filter(pk=user.pk).exists()
        assert not PrivacySettings.objects.filter(user_id=user.pk).exists()
        assert not LinkedSource.objects.filter(user_id=user.pk).exists()
        assert not ScrobbleToken.objects.filter(user_id=user.pk).exists()
        assert not PlatformConnection.objects.filter(user_id=user.pk).exists()
        assert mongo_db.listens.count_documents({}) == 1

    def test_purge_user_too_early_is_noop(self, mongo_db):
        user = self._deleted_user(mongo_db, days_ago=5)
        assert tasks.purge_user.run(str(user.pk)) is False
        assert User.objects.filter(pk=user.pk).exists()
        assert tasks.purge_user.run(str(user.pk), force=True) is True

    def test_purge_ignores_live_accounts(self, db):
        user = UserFactory()
        assert tasks.purge_user.run(str(user.pk)) is False
        assert services.purge_account(user.pk) is False

    def test_sweeper(self, mongo_db):
        old = self._deleted_user(mongo_db, days_ago=40)
        recent = self._deleted_user(mongo_db, days_ago=2)
        assert tasks.purge_due_users.run() == 1
        assert not User.objects.filter(pk=old.pk).exists()
        assert User.objects.filter(pk=recent.pk).exists()

    def test_sweeper_survives_errors(self, mongo_db):
        self._deleted_user(mongo_db, days_ago=40)
        with mock.patch("accounts.services.purge_account", side_effect=RuntimeError):
            assert tasks.purge_due_users.run() == 0

    def test_purge_retries_on_error(self, mongo_db):
        user = self._deleted_user(mongo_db)
        with (
            mock.patch("accounts.services.purge_account", side_effect=RuntimeError),
            mock.patch.object(tasks.purge_user, "retry", side_effect=RuntimeError("retry")),
            pytest.raises(RuntimeError, match="retry"),
        ):
            tasks.purge_user.run(str(user.pk))


class TestExport:
    def test_export(self, api, mongo_db):
        user = UserFactory(email="exp@example.test", college="IIT")
        _seed_sources(user)
        services.give_consent(user, "email_digest")
        _login(api, "exp@example.test")
        r = api.get("/api/v1/me/export")
        assert r.status_code == 200
        assert r["Content-Disposition"] == 'attachment; filename="jingle-export.json"'
        data = json.loads(r.content)
        assert set(data) >= {"profile", "privacy", "consents", "connections", "companion_tokens"}
        assert data["profile"]["college"] == "IIT"
        assert data["connections"][0]["platform"] == "SPOTIFY"
        text = r.content.decode()
        assert "token_ciphertext" not in text and user.pk.hex * 2 not in text
        assert "LISTENBRAINZ" not in text  # no route words (BR-14)

    def test_unauthenticated(self, api):
        assert api.get("/api/v1/me/export").status_code == 401
