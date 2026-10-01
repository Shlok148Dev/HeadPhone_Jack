"""JNG-01-01 sign-up / sign-in, ADR-0011 token handling, NFR-SEC-04 rate limits."""

from datetime import date

import jwt
import pytest
from django.conf import settings

from accounts import auth_views
from accounts.models import Consent, PrivacySettings, User
from tests.factories import PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

COOKIE = "jingle_refresh"


def register_payload(**overrides):
    body = {
        "email": "Asha@Example.test",
        "password": "a-long-unique-passphrase-7",
        "username": "asha_k",
        "display_name": "Asha",
        "birth_year": 1999,
    }
    body.update(overrides)
    return body


def _decode(token):
    return jwt.decode(
        token,
        settings.SIMPLE_JWT["SIGNING_KEY"],
        algorithms=["HS256"],
        issuer="jingle-core",
    )


class TestRegister:
    def test_happy_path_sets_cookie_claims_privacy_and_consent(self, api):
        r = api.post("/api/v1/auth/register", register_payload(), format="json")
        assert r.status_code == 201, r.content
        body = r.json()
        assert set(body) == {"access", "user"}
        assert body["user"]["username"] == "asha_k"
        assert body["user"]["email"] == "asha@example.test"
        assert "birth_year" not in body["user"]
        assert body["user"]["needs_onboarding"] is False
        assert "refresh" not in body
        claims = _decode(body["access"])
        assert claims["sub"] == body["user"]["id"]
        assert claims["typ"] == "access"
        assert claims["iss"] == "jingle-core"
        cookie = r.cookies[COOKIE]
        assert cookie["httponly"]
        assert cookie["samesite"] == "Lax"
        assert cookie["path"] == "/api/v1/auth"
        assert r["Cache-Control"] == "no-store"
        user = User.objects.get(pk=body["user"]["id"])
        assert user.check_password("a-long-unique-passphrase-7")
        assert user.password.startswith("argon2")
        assert PrivacySettings.objects.filter(user=user, activity_visibility="friends").exists()
        consent = Consent.objects.get(user=user)
        assert consent.purpose == "core_service" and consent.withdrawn_at is None

    def test_under_18_rejected(self, api):
        year = date.today().year - 17
        r = api.post("/api/v1/auth/register", register_payload(birth_year=year), format="json")
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "AGE_RESTRICTED"
        assert not User.objects.exists()

    def test_exactly_18_by_year_allowed(self, api):
        year = date.today().year - 18
        r = api.post("/api/v1/auth/register", register_payload(birth_year=year), format="json")
        assert r.status_code == 201

    @pytest.mark.parametrize(
        "username",
        ["ab", "a" * 21, "has space", "bad-dash", "émile", "admin", "fuck_you", "shit.head"],
    )
    def test_username_rules(self, api, username):
        r = api.post("/api/v1/auth/register", register_payload(username=username), format="json")
        assert r.status_code == 400
        err = r.json()["error"]
        assert err["code"] == "VALIDATION_ERROR"
        assert "username" in err["details"]

    def test_username_lowercased_and_case_insensitive_unique(self, api):
        UserFactory(username="asha_k")
        r = api.post("/api/v1/auth/register", register_payload(username="ASHA_K"), format="json")
        assert r.status_code == 400
        assert "username" in r.json()["error"]["details"]

    def test_mixed_case_username_normalised(self, api):
        r = api.post("/api/v1/auth/register", register_payload(username="Asha.K"), format="json")
        assert r.status_code == 201
        assert r.json()["user"]["username"] == "asha.k"

    def test_profane_display_name_rejected(self, api):
        r = api.post(
            "/api/v1/auth/register", register_payload(display_name="fuck off"), format="json"
        )
        assert r.status_code == 400
        assert "display_name" in r.json()["error"]["details"]

    def test_duplicate_email_rejected(self, api):
        UserFactory(email="asha@example.test")
        r = api.post("/api/v1/auth/register", register_payload(), format="json")
        assert r.status_code == 400
        assert "email" in r.json()["error"]["details"]

    def test_weak_password_rejected(self, api):
        r = api.post("/api/v1/auth/register", register_payload(password="password"), format="json")
        assert r.status_code == 400
        assert "password" in r.json()["error"]["details"]

    def test_missing_fields(self, api):
        r = api.post("/api/v1/auth/register", {}, format="json")
        assert r.status_code == 400
        details = r.json()["error"]["details"]
        assert {"email", "password", "username", "birth_year"} <= set(details)

    def test_display_name_defaults_to_username(self, api):
        r = api.post("/api/v1/auth/register", register_payload(display_name=""), format="json")
        assert r.json()["user"]["display_name"] == "asha_k"

    def test_rate_limited_5_per_minute_per_ip(self, api):
        for i in range(5):
            api.post(
                "/api/v1/auth/register",
                register_payload(username=f"u{i}x", email="x"),
                format="json",
            )
        r = api.post("/api/v1/auth/register", register_payload(), format="json")
        assert r.status_code == 429
        assert r.json()["error"]["code"] == "RATE_LIMITED"
        assert int(r["Retry-After"]) >= 1
        assert r["X-RateLimit-Limit"] == "5"


class TestLogin:
    def test_happy_path(self, api):
        user = UserFactory(email="ravi@example.test")
        r = api.post(
            "/api/v1/auth/login",
            {"email": "RAVI@example.test", "password": PASSWORD},
            format="json",
        )
        assert r.status_code == 200
        assert r.json()["user"]["id"] == str(user.pk)
        assert COOKIE in r.cookies

    def test_wrong_password(self, api):
        UserFactory(email="ravi@example.test")
        r = api.post(
            "/api/v1/auth/login",
            {"email": "ravi@example.test", "password": "nope-nope"},
            format="json",
        )
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_unknown_email_same_error(self, api):
        r = api.post(
            "/api/v1/auth/login",
            {"email": "ghost@example.test", "password": "x" * 9},
            format="json",
        )
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_inactive_user_rejected(self, api):
        UserFactory(email="gone@example.test", is_active=False)
        r = api.post(
            "/api/v1/auth/login",
            {"email": "gone@example.test", "password": PASSWORD},
            format="json",
        )
        assert r.status_code == 401

    def test_validation_error(self, api):
        r = api.post("/api/v1/auth/login", {"email": "not-an-email"}, format="json")
        assert r.status_code == 400

    def test_rate_limit_10_per_minute_per_ip_and_email(self, api):
        UserFactory(email="ravi@example.test")
        body = {"email": "ravi@example.test", "password": "wrong-password"}
        for _ in range(10):
            assert api.post("/api/v1/auth/login", body, format="json").status_code == 401
        assert api.post("/api/v1/auth/login", body, format="json").status_code == 429
        other = {"email": "someone@example.test", "password": "wrong-password"}
        assert api.post("/api/v1/auth/login", other, format="json").status_code == 401


class TestRefreshLogout:
    def _login(self, api):
        UserFactory(email="kabir@example.test")
        r = api.post(
            "/api/v1/auth/login",
            {"email": "kabir@example.test", "password": PASSWORD},
            format="json",
        )
        return r.cookies[COOKIE].value

    def test_refresh_rotates_and_blacklists_old(self, api, fake_redis):
        old = self._login(api)
        r = api.post("/api/v1/auth/refresh")
        assert r.status_code == 200
        new = r.cookies[COOKIE].value
        assert new != old
        assert _decode(r.json()["access"])["typ"] == "access"
        # R-E: a page that navigated mid-refresh re-presents the old cookie within 30 s: allowed.
        api.cookies[COOKIE] = old
        assert api.post("/api/v1/auth/refresh").status_code == 200
        # After the grace window the rotated token is dead for good.
        for k in fake_redis.scan_iter("refresh:grace:*"):
            fake_redis.delete(k)
        api.cookies[COOKIE] = old
        assert api.post("/api/v1/auth/refresh").status_code == 401

    def test_logged_out_token_gets_no_grace(self, api, fake_redis):
        tok = self._login(api)
        api.post("/api/v1/auth/logout")
        api.cookies[COOKIE] = tok
        r2 = api.post("/api/v1/auth/refresh")
        assert r2.status_code == 401
        assert r2.json()["error"]["code"] == "REFRESH_INVALID"

    def test_refresh_without_cookie(self, api):
        r = api.post("/api/v1/auth/refresh")
        assert r.status_code == 401

    def test_refresh_with_garbage(self, api):
        api.cookies[COOKIE] = "not-a-token"
        assert api.post("/api/v1/auth/refresh").status_code == 401

    def test_refresh_rejects_access_token(self, api):
        UserFactory(email="kabir@example.test")
        r = api.post(
            "/api/v1/auth/login",
            {"email": "kabir@example.test", "password": PASSWORD},
            format="json",
        )
        api.cookies[COOKIE] = r.json()["access"]
        assert api.post("/api/v1/auth/refresh").status_code == 401

    def test_refresh_for_deactivated_user(self, api):
        self._login(api)
        User.objects.update(is_active=False)
        assert api.post("/api/v1/auth/refresh").status_code == 401

    def test_logout_blacklists_and_clears_cookie(self, api):
        old = self._login(api)
        r = api.post("/api/v1/auth/logout")
        assert r.status_code == 204
        assert r.cookies[COOKIE].value == ""
        api.cookies[COOKIE] = old
        assert api.post("/api/v1/auth/refresh").status_code == 401

    def test_logout_without_cookie_or_with_garbage(self, api):
        assert api.post("/api/v1/auth/logout").status_code == 204
        api.cookies[COOKIE] = "garbage"
        assert api.post("/api/v1/auth/logout").status_code == 204

    def test_access_token_authenticates(self, api):
        UserFactory(email="kabir@example.test")
        r = api.post(
            "/api/v1/auth/login",
            {"email": "kabir@example.test", "password": PASSWORD},
            format="json",
        )
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
        assert api.get("/api/v1/me").status_code == 200


class TestGoogle:
    CLAIMS = {
        "sub": "google-123",
        "email": "Meera@Gmail.test",
        "email_verified": True,
        "name": "Meera Rao",
    }

    @pytest.fixture
    def google_on(self, settings, monkeypatch):
        settings.GOOGLE_OAUTH_CLIENT_ID = "client-id.apps.googleusercontent.com"
        calls = {}

        def fake_verify(token):
            calls["token"] = token
            if token == "bad":
                raise ValueError("bad token")
            return dict(self.CLAIMS)

        monkeypatch.setattr(auth_views, "verify_google_id_token", fake_verify)
        return calls

    def test_disabled_without_client_id(self, api, settings):
        settings.GOOGLE_OAUTH_CLIENT_ID = ""
        r = api.post("/api/v1/auth/google", {"id_token": "x"}, format="json")
        assert r.status_code == 503
        assert r.json()["error"]["code"] == "GOOGLE_SIGNIN_DISABLED"

    def test_first_sign_in_creates_user_needing_onboarding(self, api, google_on):
        r = api.post("/api/v1/auth/google", {"id_token": "good"}, format="json")
        assert r.status_code == 201, r.content
        body = r.json()
        assert body["created"] is True
        assert body["user"]["username"] == "meera"
        assert body["user"]["display_name"] == "Meera Rao"
        assert body["user"]["needs_onboarding"] is True
        user = User.objects.get(google_sub="google-123")
        assert not user.has_usable_password()
        assert user.email == "meera@gmail.test"
        assert Consent.objects.filter(user=user, purpose="core_service").exists()
        assert COOKIE in r.cookies

    def test_second_sign_in_logs_in(self, api, google_on):
        api.post("/api/v1/auth/google", {"id_token": "good"}, format="json")
        r = api.post("/api/v1/auth/google", {"id_token": "good"}, format="json")
        assert r.status_code == 200
        assert r.json()["created"] is False
        assert User.objects.count() == 1

    def test_username_collision_gets_suffix(self, api, google_on):
        UserFactory(username="meera")
        r = api.post("/api/v1/auth/google", {"id_token": "good"}, format="json")
        username = r.json()["user"]["username"]
        assert username.startswith("meera") and username != "meera"
        assert len(username) <= 20

    def test_invalid_token(self, api, google_on):
        r = api.post("/api/v1/auth/google", {"id_token": "bad"}, format="json")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "GOOGLE_TOKEN_INVALID"

    def test_unverified_email_rejected(self, api, google_on, monkeypatch):
        monkeypatch.setattr(
            auth_views,
            "verify_google_id_token",
            lambda t: {**self.CLAIMS, "email_verified": False},
        )
        r = api.post("/api/v1/auth/google", {"id_token": "good"}, format="json")
        assert r.status_code == 401

    def test_existing_password_account_not_silently_linked(self, api, google_on):
        UserFactory(email="meera@gmail.test")
        r = api.post("/api/v1/auth/google", {"id_token": "good"}, format="json")
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "ACCOUNT_EXISTS"

    def test_deactivated_google_user_rejected(self, api, google_on):
        api.post("/api/v1/auth/google", {"id_token": "good"}, format="json")
        User.objects.update(is_active=False)
        r = api.post("/api/v1/auth/google", {"id_token": "good"}, format="json")
        assert r.status_code == 401

    def test_profane_name_not_used(self, api, google_on, monkeypatch):
        monkeypatch.setattr(
            auth_views,
            "verify_google_id_token",
            lambda t: {**self.CLAIMS, "name": "shit head", "email": "x!@gmail.test"},
        )
        r = api.post("/api/v1/auth/google", {"id_token": "good"}, format="json")
        assert r.status_code == 201
        user = r.json()["user"]
        assert user["username"] == "listener"
        assert user["display_name"] == "listener"

    def test_missing_id_token(self, api, google_on):
        assert api.post("/api/v1/auth/google", {}, format="json").status_code == 400

    def test_real_verifier_is_called_with_client_id(self, settings, monkeypatch):
        settings.GOOGLE_OAUTH_CLIENT_ID = "cid"
        seen = {}

        def fake(token, request, audience):
            seen.update(token=token, audience=audience)
            return {"sub": "1"}

        monkeypatch.setattr("google.oauth2.id_token.verify_oauth2_token", fake)
        assert auth_views.verify_google_id_token("tok") == {"sub": "1"}
        assert seen == {"token": "tok", "audience": "cid"}
