import fakeredis
import mongomock
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from core_api import mongo, redis_client

from .factories import UserFactory


@pytest.fixture(autouse=True)
def _isolated_stores():
    """Every test gets a fresh fakeredis, mongomock database and empty cache."""
    fake = fakeredis.FakeRedis(decode_responses=True)
    db = mongomock.MongoClient().db
    redis_client.set_client(fake)
    mongo.set_db(db)
    cache.clear()
    yield
    redis_client.set_client(None)
    mongo.set_db(None)
    cache.clear()


@pytest.fixture
def fake_redis():
    return redis_client.get_redis()


@pytest.fixture
def mongo_db():
    return mongo.get_db()


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def auth_api(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture(autouse=True)
def ingest_deletions(monkeypatch):
    """Record calls to ingest-ml's data-deletion endpoint instead of making HTTP requests."""
    calls: list = []

    def fake(user_id) -> bool:
        calls.append(str(user_id))
        return True

    monkeypatch.setattr("sources.views.delete_ingest_data", fake)
    return calls
