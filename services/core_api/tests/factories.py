import json
import time
import uuid

import factory

from accounts.models import PrivacySettings, User

PASSWORD = "correct-horse-battery-9"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n:04d}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.test")
    display_name = factory.LazyAttribute(lambda o: o.username.title())
    birth_year = 1995

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):  # noqa: N805
        obj.set_password(extracted or PASSWORD)
        if create:
            obj.save(update_fields=["password"])

    @factory.post_generation
    def privacy(obj, create, extracted, **kwargs):  # noqa: N805
        if create:
            PrivacySettings.objects.get_or_create(user=obj, defaults=extracted or {})


def listen_event(user_id, *, platform="SPOTIFY", via="COMPANION", kind="NOW_PLAYING",
                 title="Kill Bill", artist="SZA", observed_at=None, recording_id=None):
    observed_at = observed_at if observed_at is not None else time.time()
    return {
        "event_id": str(uuid.uuid4()),
        "user_id": str(user_id),
        "recording_id": str(recording_id) if recording_id else None,
        "raw": {"artist": artist, "title": title, "album": "SOS", "duration_ms": 153000},
        "artwork_url": "https://img.example/art.jpg",
        "platform": platform,
        "via": via,
        "kind": kind,
        "played_at": "2026-09-29T10:15:02Z",
        "observed_at": "2026-09-29T10:15:20Z",
        "trainable": True,
    }


def put_signal(redis, key_prefix, user_id, *, observed_at, platform="SPOTIFY", via="COMPANION",
               **kwargs):
    """Write an ``np:``/``last:`` hash exactly as ingest-ml does (CONTRACTS.md §6)."""
    event = listen_event(user_id, platform=platform, via=via, observed_at=observed_at, **kwargs)
    redis.hset(
        f"{key_prefix}:{user_id}",
        mapping={
            "event": json.dumps(event),
            "observed_at": str(observed_at),
            "via": via,
            "platform": platform,
        },
    )
    return event
