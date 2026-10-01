"""core_api building blocks: rate limit, idempotency, pagination, events, flags, internal, policy."""

import json
from datetime import timedelta
from unittest import mock

import pytest
import redis
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from accounts.models import User
from core_api import events, flags, mongo, policy, redis_client
from core_api.idempotency import idempotent
from core_api.models import FeatureFlag
from core_api.pagination import CursorPagination
from core_api.ratelimit import _key_for, client_ip, hit, parse_rate, ratelimit
from tests.factories import UserFactory

rf = APIRequestFactory()


# ---------------------------------------------------------------- rate limit


class TestRateLimit:
    def test_parse_rate(self):
        assert parse_rate("10/m") == (10, 60)
        assert parse_rate("5/h") == (5, 3600)
        assert parse_rate("1/s") == (1, 1)
        assert parse_rate("30/day") == (30, 86400)

    def test_bucket_refills(self):
        for _ in range(2):
            assert hit("t", "k", "2/m", now=1000)[0]
        allowed, remaining, wait = hit("t", "k", "2/m", now=1000)
        assert (allowed, remaining) == (False, 0) and wait == 30
        assert hit("t", "k", "2/m", now=1031)[0]

    def test_client_ip_uses_rightmost_forwarded(self):
        req = rf.get("/", HTTP_X_FORWARDED_FOR="6.6.6.6, 10.0.0.9", REMOTE_ADDR="172.18.0.2")
        assert client_ip(req) == "10.0.0.9"
        assert client_ip(rf.get("/", REMOTE_ADDR="1.2.3.4")) == "1.2.3.4"

    @pytest.mark.django_db
    def test_keys(self):
        req = rf.get("/")
        req.user = mock.Mock(is_authenticated=True, pk="u1")
        assert _key_for(req, "user") == "u:u1"
        req.user = mock.Mock(is_authenticated=False)
        assert _key_for(req, "user").startswith("ip:")
        assert _key_for(req, lambda r: "custom") == "custom"
        req.data = ["not-a-dict"]
        assert _key_for(req, "ip+email").endswith("|")
        with pytest.raises(ValueError):
            _key_for(req, "nope")

    def test_decorator_on_view(self):
        class V(APIView):
            authentication_classes: list = []
            permission_classes: list = []

            @ratelimit(key="ip", rate="1/m")
            def get(self, request):
                return Response({"ok": True})

        view = V.as_view()
        assert view(rf.get("/")).status_code == 200
        r = view(rf.get("/"))
        assert r.status_code == 429
        assert r.data["error"]["code"] == "RATE_LIMITED"
        assert r["Retry-After"] == "60"


# ---------------------------------------------------------------- idempotency


class _CreateView(APIView):
    calls = 0

    @idempotent
    def post(self, request):
        _CreateView.calls += 1
        return Response({"n": _CreateView.calls}, status=201)


class _OptionalView(APIView):
    @idempotent(required=False)
    def post(self, request):
        return Response({"ok": True}, status=201)


@pytest.mark.django_db
class TestIdempotency:
    def _post(self, view, user, key=None):
        headers = {"HTTP_IDEMPOTENCY_KEY": key} if key is not None else {}
        req = rf.post("/x", {}, format="json", **headers)
        force_authenticate(req, user=user)
        return view(req)

    def test_replay_returns_stored_response(self):
        user = UserFactory()
        view = _CreateView.as_view()
        _CreateView.calls = 0
        r1 = self._post(view, user, "k1")
        r2 = self._post(view, user, "k1")
        assert r1.status_code == r2.status_code == 201
        assert r1.data == r2.data == {"n": 1}
        assert r2["Idempotent-Replayed"] == "true"
        assert self._post(view, user, "k2").data == {"n": 2}
        # keys are per user
        assert self._post(view, UserFactory(), "k1").data == {"n": 3}

    def test_missing_key(self):
        r = self._post(_CreateView.as_view(), UserFactory())
        assert r.status_code == 400
        assert r.data["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    def test_optional_key(self):
        assert self._post(_OptionalView.as_view(), UserFactory()).status_code == 201

    def test_key_too_long(self):
        assert self._post(_CreateView.as_view(), UserFactory(), "x" * 201).status_code == 400

    def test_in_progress(self):
        user = UserFactory()
        with mock.patch.object(cache, "add", return_value=False):
            r = self._post(_CreateView.as_view(), user, "busy")
        assert r.status_code == 409
        assert r.data["error"]["code"] == "IDEMPOTENCY_IN_PROGRESS"


# ---------------------------------------------------------------- pagination


class _UserList(APIView):
    def get(self, request):
        paginator = CursorPagination()
        page = paginator.paginate_queryset(User.objects.all(), request, view=self)
        return paginator.get_paginated_response([str(u.pk) for u in page])


@pytest.mark.django_db
def test_cursor_pagination_shape():
    user = UserFactory()
    for _ in range(4):
        UserFactory()
    view = _UserList.as_view()
    req = rf.get("/x", {"limit": 2})
    force_authenticate(req, user=user)
    r = view(req)
    assert set(r.data) == {"results", "next_cursor"}
    assert len(r.data["results"]) == 2 and r.data["next_cursor"]
    seen = list(r.data["results"])
    cursor = r.data["next_cursor"]
    while cursor:
        req = rf.get("/x", {"limit": 2, "cursor": cursor})
        force_authenticate(req, user=user)
        r = view(req)
        seen += r.data["results"]
        cursor = r.data["next_cursor"]
    assert len(set(seen)) == 5
    schema = CursorPagination().get_paginated_response_schema({"type": "array"})
    assert schema["required"] == ["results", "next_cursor"]
    req = rf.get("/x", {"limit": 500})
    force_authenticate(req, user=user)
    assert len(view(req).data["results"]) == 5  # capped at 100


# ---------------------------------------------------------------- events / clients


def test_publish_writes_stream(fake_redis):
    entry = events.publish_domain("feed.invalidate", {"user_id": "u1"})
    assert entry
    ((_, fields),) = fake_redis.xrange("events:domain")
    assert fields["type"] == "feed.invalidate"
    assert json.loads(fields["data"]) == {"user_id": "u1"}


def test_publish_is_noop_safe_when_redis_down(monkeypatch):
    broken = mock.Mock()
    broken.xadd.side_effect = redis.ConnectionError("down")
    monkeypatch.setattr(events, "get_redis", lambda: broken)
    assert events.publish("events:domain", "x", {}) is None


def test_real_clients_are_constructed_lazily(settings):
    redis_client.set_client(None)
    client = redis_client.get_redis()
    assert isinstance(client, redis.Redis)
    assert redis_client.get_redis() is client
    mongo.set_db(None)
    settings.MONGO_URL = "mongodb://localhost:1/jingle"
    db = mongo.get_db()
    assert db is not None and db.name == "jingle"


def test_mongo_client_error_returns_none(monkeypatch):
    mongo.set_db(None)
    with mock.patch("pymongo.MongoClient", side_effect=RuntimeError):
        assert mongo.get_db() is None


# ---------------------------------------------------------------- flags


@pytest.mark.django_db
class TestFlags:
    def test_seeded_defaults(self):
        assert flags.is_enabled("spotify_direct_enabled") is True
        for name in (
            "apple_music_enabled",
            "amazon_music_enabled",
            "google_dataportability_enabled",
            "concerts_enabled",
        ):
            assert flags.is_enabled(name) is False
        assert flags.is_enabled("does_not_exist") is False
        assert flags.is_enabled("does_not_exist", default=True) is True

    def test_cached_and_invalidated_on_save(self, django_assert_num_queries):
        flags.is_enabled("concerts_enabled")
        with django_assert_num_queries(0):
            flags.is_enabled("concerts_enabled")
        FeatureFlag.objects.filter(name="concerts_enabled").update(enabled=True)
        assert flags.is_enabled("concerts_enabled") is False  # still cached (30 s)
        flag = FeatureFlag.objects.get(name="concerts_enabled")
        flag.save()
        assert flags.is_enabled("concerts_enabled") is True
        flag.delete()
        assert flags.is_enabled("concerts_enabled") is False

    def test_mirrored_to_redis(self, fake_redis):
        flags.all_flags()
        assert fake_redis.hget("flags:cache", "spotify_direct_enabled") == "1"
        assert 0 < fake_redis.ttl("flags:cache") <= 30

    def test_mirror_failure_tolerated(self, monkeypatch):
        broken = mock.Mock()
        broken.pipeline.side_effect = redis.ConnectionError
        monkeypatch.setattr(flags, "get_redis", lambda: broken)
        assert flags.is_enabled("spotify_direct_enabled") is True
        flags._mirror_to_redis({})

    def test_endpoint_public_flags(self, api, settings):
        FeatureFlag.objects.create(name="secret_thing", enabled=True, public=False)
        settings.GOOGLE_OAUTH_CLIENT_ID = ""
        r = api.get("/api/v1/flags")
        assert r.status_code == 200
        body = r.json()
        assert body["flags"]["amazon_music_enabled"] is False
        assert body["flags"]["spotify_direct_enabled"] is True
        assert "secret_thing" not in body["flags"]
        assert body["google_signin_enabled"] is False
        assert str(FeatureFlag.objects.get(name="secret_thing")) == "secret_thing=on"


# ---------------------------------------------------------------- internal routes


@pytest.mark.django_db
class TestInternal:
    URL = "/internal/users/7b1f1c1e-5d9a-4f61-9d2e-3c3a7b0e4a11/friends"

    def test_requires_service_token(self, api):
        assert api.get(self.URL).status_code == 403
        assert api.get(self.URL, HTTP_X_SERVICE_TOKEN="wrong").status_code == 403

    def test_friends_empty_for_now(self, api, settings):
        r = api.get(self.URL, HTTP_X_SERVICE_TOKEN=settings.SERVICE_TOKEN)
        assert r.status_code == 200 and r.json() == []

    @override_settings(SERVICE_TOKEN="")
    def test_unset_token_denies_everything(self, api):
        assert api.get(self.URL, HTTP_X_SERVICE_TOKEN="").status_code == 403

    def test_not_in_public_schema(self):
        from drf_spectacular.generators import SchemaGenerator

        schema = SchemaGenerator().get_schema(request=None, public=True)
        assert not any(p.startswith("/internal") for p in schema["paths"])


# ---------------------------------------------------------------- policy


@pytest.mark.django_db
class TestPolicy:
    def test_owner_always(self):
        u = UserFactory(private_until=timezone.now() + timedelta(hours=1))
        assert policy.can_view_activity(u, u)

    def test_stubs_default_closed(self):
        a, b = UserFactory(), UserFactory()
        assert policy.is_blocked_either_way(a, b) is False
        assert policy.are_friends(a, b) is False
        assert policy.share_circle(a, b) is False
        assert policy.can_view_activity(a, b) is False
        assert policy.can_view_activity(None, b) is False

    def test_rules_with_friendship(self, monkeypatch):
        a, b = UserFactory(), UserFactory()
        monkeypatch.setattr(policy, "are_friends", lambda x, y: True)
        assert policy.can_view_activity(a, b)
        monkeypatch.setattr(policy, "is_blocked_either_way", lambda x, y: True)
        assert not policy.can_view_activity(a, b)

    def test_deleted_owner_hidden(self, monkeypatch):
        monkeypatch.setattr(policy, "are_friends", lambda x, y: True)
        a, b = UserFactory(), UserFactory(deleted_at=timezone.now())
        assert not policy.can_view_activity(a, b)

    def test_circles_visibility(self, monkeypatch):
        a, b = UserFactory(), UserFactory()
        b.privacy.activity_visibility = "circles"
        b.privacy.save()
        assert not policy.can_view_activity(a, b)
        monkeypatch.setattr(policy, "share_circle", lambda x, y: True)
        b._privacy_cache = None
        assert policy.can_view_activity(a, b)
