"""Celery ML jobs (queue ``ml``; Tech Bible 5, 7.4). Idempotent: results overwrite the cache."""

from __future__ import annotations

import json
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

log = logging.getLogger(__name__)
CACHE_TTL = 24 * 3600
DISMISS_DAYS = 90


def cache_key(user_id) -> str:
    return f"sug:{user_id}"


def load_graph():
    from accounts.models import ActivityVisibility, PrivacySettings, User
    from jingle_ml.suggest import Graph, Person
    from social.models import Block, Friendship, FriendshipStatus
    from suggestions.models import FeedbackAction, SuggestionFeedback

    now = timezone.now()
    year = now.year
    nobody = set(
        PrivacySettings.objects.filter(activity_visibility=ActivityVisibility.NOBODY).values_list(
            "user_id", flat=True
        )
    )
    people, display = {}, {}
    for u in User.objects.filter(is_active=True, deleted_at__isnull=True):
        uid = str(u.pk)
        people[uid] = Person(
            id=uid,
            discoverable=u.discoverable,
            adult=bool(u.birth_year and year - u.birth_year >= 18),
            college=u.college or "",
            city=u.city or "",
            private=bool(u.private_until and u.private_until > now) or u.pk in nobody,
        )
        display[uid] = u.display_name or u.username
    friends: dict[str, set[str]] = {uid: set() for uid in people}
    pending: set[frozenset[str]] = set()
    for lo, hi, st in Friendship.objects.values_list("user_low_id", "user_high_id", "status"):
        a, b = str(lo), str(hi)
        if st == FriendshipStatus.ACCEPTED:
            friends.setdefault(a, set()).add(b)
            friends.setdefault(b, set()).add(a)
        else:
            pending.add(frozenset((a, b)))
    blocked = {
        frozenset((str(a), str(b)))
        for a, b in Block.objects.values_list("blocker_id", "blocked_id")
    }
    dismissed: dict[str, set[str]] = {}
    since = now - timedelta(days=DISMISS_DAYS)
    for u, c in SuggestionFeedback.objects.filter(
        action=FeedbackAction.DISMISSED, at__gte=since
    ).values_list("user_id", "candidate_id"):
        dismissed.setdefault(str(u), set()).add(str(c))
    return Graph(
        people=people,
        friends=friends,
        pending=pending,
        blocked=blocked,
        dismissed=dismissed,
        display=display,
    )


def load_taste():
    from jingle_ml import data, taste
    from suggestions.models import TasteSeed

    counts = data.artist_counts(purpose="train")  # lineage: trainable listens only
    seeds = {
        str(s.user_id): {"artists": s.artists, "genres": s.genres} for s in TasteSeed.objects.all()
    }
    vecs = taste.vectors(taste.documents(counts, seeds))
    return vecs, taste.top_artists(counts, seeds)


def _upsert_qdrant(vecs) -> None:
    """ADR-0008: keep taste vectors in Qdrant for ANN at scale. Best effort; pilot uses NumPy."""
    try:
        from django.conf import settings
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, PointStruct, VectorParams

        if not vecs:
            return
        dim = len(next(iter(vecs.values())))
        client = QdrantClient(url=settings.QDRANT_URL, timeout=5)
        name = f"taste_vectors_{dim}"
        if not client.collection_exists(name):
            client.create_collection(
                name, vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
            )
        client.upsert(
            name, [PointStruct(id=uid, vector=v.tolist(), payload={}) for uid, v in vecs.items()]
        )
    except Exception:  # noqa: BLE001 - Qdrant down must not stop suggestions
        log.warning("qdrant upsert skipped")


def compute(user_ids: list[str] | None = None) -> dict[str, int]:
    from core_api.redis_client import get_redis
    from jingle_ml.suggest import suggest_for
    from jingle_ml.tracking import log_run

    g = load_graph()
    vecs, tops = load_taste()
    targets = user_ids or list(g.people)
    r = get_redis()
    counts = {"users": 0, "suggestions": 0, "empty": 0}
    for uid in targets:
        out = suggest_for(g, uid, vecs, tops)
        payload = [
            {
                "user_id": s.user_id,
                "score": s.score,
                "reasons": s.reasons,
                "source_signals": s.source_signals,
            }
            for s in out
        ]
        r.set(cache_key(uid), json.dumps(payload), ex=CACHE_TTL)
        counts["users"] += 1
        counts["suggestions"] += len(payload)
        counts["empty"] += int(not payload)
    if user_ids is None:
        _upsert_qdrant(vecs)
        log_run(
            "suggestions", params={"users": len(g.people), "vectors": len(vecs)}, metrics=counts
        )
    return counts


@shared_task(queue="ml", ignore_result=True, soft_time_limit=600)
def recompute_all() -> dict[str, int]:
    """Nightly at 03:00 IST (Tech Bible 7.4)."""
    return compute(None)


@shared_task(queue="ml", ignore_result=True, soft_time_limit=120)
def recompute_users(user_ids: list[str]) -> dict[str, int]:
    """Within 60 s of a first friendship or new taste picks (Tech Bible 5.3)."""
    return compute([str(u) for u in user_ids])


def schedule_recompute(*user_ids) -> None:
    """Enqueue from the API process (which doesn't ship the ML libraries) without importing them."""
    from core_api.celery_app import app

    try:
        app.send_task(
            "jingle_ml.tasks.recompute_users",
            args=[[str(u) for u in user_ids]],
            queue="ml",
            countdown=5,
        )
    except Exception:  # noqa: BLE001 - broker down: the nightly run catches up
        log.warning("could not enqueue suggestion recompute")
