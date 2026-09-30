"""Data loading for ML jobs, with lineage enforced in one place (jingle-ml-job skill).

``purpose="train"`` (anything that builds a model or profile, e.g. taste vectors) keeps only
listens with ``trainable=True``: never direct-Spotify API data (Policy III.13/III.14) or Last.fm
data (BR-04). ``purpose="display"`` also requires ``analytics_allowed`` for anything aggregated.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta

from django.utils import timezone

PURPOSE_FILTERS = {
    "train": {"trainable": True},
    "display": {"analytics_allowed": {"$ne": False}},
}


def listen_filter(purpose: str, since_days: int = 90) -> dict:
    if purpose not in PURPOSE_FILTERS:
        raise ValueError(f"unknown purpose {purpose!r}")
    return {
        "played_at": {"$gte": timezone.now() - timedelta(days=since_days)},
        **PURPOSE_FILTERS[purpose],
    }


def artist_counts(purpose: str = "train", since_days: int = 90) -> dict[str, Counter[str]]:
    from core_api.mongo import get_db

    db = get_db()
    if db is None:
        return {}
    out: dict[str, Counter[str]] = defaultdict(Counter)
    pipeline = [
        {"$match": listen_filter(purpose, since_days)},
        {"$group": {"_id": {"u": "$meta.user_id", "a": "$raw.artist"}, "n": {"$sum": 1}}},
    ]
    for row in db.listens.aggregate(pipeline):
        uid, artist = row["_id"].get("u"), row["_id"].get("a")
        if uid and artist:
            out[str(uid)][str(artist)] += int(row["n"])
    return dict(out)
