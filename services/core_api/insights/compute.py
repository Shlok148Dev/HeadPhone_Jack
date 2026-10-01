"""Compatibility, stats and taste timeline (Technical Bible 6.1; EP-08; ADR-0022).

Everything here reads only analysable listens (``analytics_allowed``), so direct-Spotify API
data (BR-03) never becomes a score, a stat or a timeline point.
"""

from __future__ import annotations

import bisect
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from django.db.models.functions import Lower
from django.utils import timezone

WINDOW_DAYS = 90
TOP_ARTISTS = 50
MIN_PLAYS = 20  # below this a score would be noise: say "not enough listening yet"
READY_DAYS = 14  # JNG-08-06: analytics build over 2–4 weeks
DEFAULT_TRACK_MS = 210_000  # when a play has no duration, count ~3.5 min and say "about"
W_WITH_SOUND = {"artists": 0.45, "genres": 0.30, "sound": 0.25}
W_NO_SOUND = {"artists": 0.60, "genres": 0.40}
DIST_KEY = "compat:dist"
MIN_DIST = 20
SOUND_UNAVAILABLE = "Sound comparison unavailable"


def _match(uid: str, since: datetime, until: datetime | None = None) -> dict:
    played: dict = {"$gte": since}
    if until is not None:
        played["$lt"] = until
    return {"meta.user_id": uid, "played_at": played, "analytics_allowed": {"$ne": False}}


def _db():
    from core_api.mongo import get_db

    return get_db()


def artist_plays(uid: str, since: datetime, until: datetime | None = None) -> tuple[Counter, dict]:
    """Plays per artist (lower-cased key) and a display name for each."""
    db = _db()
    if db is None:
        return Counter(), {}
    rows = db.listens.aggregate(
        [
            {"$match": _match(uid, since, until)},
            {
                "$group": {
                    "_id": {"$toLower": "$raw.artist"},
                    "n": {"$sum": 1},
                    "name": {"$first": "$raw.artist"},
                }
            },
        ]
    )
    counts, names = Counter(), {}
    for r in rows:
        if r.get("_id"):
            key = " ".join(r["_id"].split())
            counts[key] += r["n"]
            names.setdefault(key, r.get("name") or key)
    return counts, names


def genre_tags(artists: set[str]) -> dict[str, dict[str, float]]:
    """MusicBrainz tags per artist (lower-cased name), weights normalised per artist."""
    from sources.models import ArtistTag

    if not artists:
        return {}
    out: dict[str, dict[str, float]] = defaultdict(dict)
    rows = (
        ArtistTag.objects.annotate(n=Lower("artist__name"))
        .filter(n__in=list(artists))
        .values_list("n", "tag", "weight")
    )
    for name, tag, w in rows:
        out[name][tag.lower()] = float(w)
    for name, tags in out.items():
        total = sum(tags.values()) or 1.0
        out[name] = {t: w / total for t, w in tags.items()}
    return out


def shares(counts: Counter, top: int = TOP_ARTISTS) -> dict[str, float]:
    best = counts.most_common(top)
    total = sum(n for _, n in best) or 1
    return {a: n / total for a, n in best}


def weighted_jaccard(p: dict[str, float], q: dict[str, float]) -> float:
    keys = set(p) | set(q)
    num = sum(min(p.get(k, 0.0), q.get(k, 0.0)) for k in keys)
    den = sum(max(p.get(k, 0.0), q.get(k, 0.0)) for k in keys)
    return num / den if den else 0.0


def genre_vector(
    artist_share: dict[str, float], tags: dict[str, dict[str, float]]
) -> dict[str, float]:
    g: Counter = Counter()
    for a, s in artist_share.items():
        for t, w in tags.get(a, {}).items():
            g[t] += s * w
    return dict(g)


def cosine(p: dict[str, float], q: dict[str, float]) -> float:
    dot = sum(v * q.get(k, 0.0) for k, v in p.items())
    np_, nq = math.sqrt(sum(v * v for v in p.values())), math.sqrt(sum(v * v for v in q.values()))
    return dot / (np_ * nq) if np_ and nq else 0.0


@dataclass
class Compat:
    ready: bool
    raw: float = 0.0
    components: dict | None = None
    shared_artists: list | None = None
    shared_genres: list | None = None
    genres_available: bool = False


def compatibility(u_counts: Counter, v_counts: Counter, names: dict, tags: dict) -> Compat:
    """Tech Bible 6.1 raw score. Sound needs ≥ 20 analysed recordings each: never true in the
    pilot (no audio analysis), so the no-sound weights apply and the card says so."""
    if sum(u_counts.values()) < MIN_PLAYS or sum(v_counts.values()) < MIN_PLAYS:
        return Compat(ready=False)
    pu, pv = shares(u_counts), shares(v_counts)
    artists = weighted_jaccard(pu, pv)
    gu, gv = genre_vector(pu, tags), genre_vector(pv, tags)
    genres_ok = bool(gu) and bool(gv)
    genres = cosine(gu, gv) if genres_ok else 0.0
    weights = dict(W_NO_SOUND) if genres_ok else {"artists": 1.0}
    comps = {"artists": artists, **({"genres": genres} if genres_ok else {})}
    raw = sum(weights[k] * comps[k] for k in comps)
    shared = sorted(set(pu) & set(pv), key=lambda a: -(pu[a] + pv[a]))
    shared_g = sorted(set(gu) & set(gv), key=lambda g: -(gu[g] + gv[g])) if genres_ok else []
    return Compat(
        ready=True,
        raw=raw,
        components={k: {"value": comps[k], "weight": weights[k]} for k in comps},
        shared_artists=[names.get(a, a) for a in shared[:10]],
        shared_genres=shared_g[:6],
        genres_available=genres_ok,
    )


def percentile(raw: float, dist: list[float]) -> tuple[int, bool]:
    """F_pairs: where this pair sits among all friend pairs (50 = a typical friendship).
    With too few pairs to calibrate, fall back to the raw value and say it isn't calibrated."""
    if len(dist) < MIN_DIST:
        return round(100 * raw), False
    lo = bisect.bisect_left(dist, raw)
    hi = bisect.bisect_right(dist, raw)
    return round(100 * ((lo + hi) / 2) / len(dist)), True


def load_dist() -> list[float]:
    from core_api.redis_client import get_redis

    try:
        v = get_redis().get(DIST_KEY)
        return sorted(json.loads(v)) if v else []
    except Exception:  # noqa: BLE001
        return []


def recalibrate() -> int:
    """Monthly: raw scores over every accepted friendship (numbers only, no identities)."""
    from core_api.redis_client import get_redis
    from social.models import Friendship, FriendshipStatus

    since = timezone.now() - timedelta(days=WINDOW_DAYS)
    cache: dict[str, tuple[Counter, dict]] = {}

    def plays(uid: str):
        if uid not in cache:
            cache[uid] = artist_plays(uid, since)
        return cache[uid]

    pairs = Friendship.objects.filter(status=FriendshipStatus.ACCEPTED).values_list(
        "user_low_id", "user_high_id"
    )
    raws = []
    for a, b in pairs:
        (ca, na), (cb, nb) = plays(str(a)), plays(str(b))
        tags = genre_tags(set(ca) | set(cb))
        c = compatibility(ca, cb, {**na, **nb}, tags)
        if c.ready:
            raws.append(round(c.raw, 5))
    get_redis().set(DIST_KEY, json.dumps(sorted(raws)))
    return len(raws)


# ---- my stats + timeline (JNG-08-03, 08-06, 08-07) -----------------------------------------


def my_stats(uid: str, now: datetime | None = None) -> dict:
    now = now or timezone.now()
    db = _db()
    since = now - timedelta(days=30)
    first = None
    if db is not None:
        doc = db.listens.find_one(
            {"meta.user_id": uid, "analytics_allowed": {"$ne": False}}, sort=[("played_at", 1)]
        )
        first = doc.get("played_at") if doc else None
    if first is not None and timezone.is_naive(first):
        first = first.replace(tzinfo=UTC)  # Mongo returns naive UTC
    days = max(0, (now - first).days) if first else 0
    out: dict = {
        "ready": days >= READY_DAYS,
        "days_of_data": days,
        "ready_in_days": max(0, READY_DAYS - days),
    }
    if db is None:
        return {**out, "ready": False, "degraded": True}
    rows = list(
        db.listens.aggregate(
            [
                {"$match": _match(uid, since)},
                {
                    "$group": {
                        "_id": {"a": {"$toLower": "$raw.artist"}, "p": "$meta.platform"},
                        "n": {"$sum": 1},
                        "ms": {"$sum": {"$ifNull": ["$raw.duration_ms", DEFAULT_TRACK_MS]}},
                        "name": {"$first": "$raw.artist"},
                    }
                },
            ]
        )
    )
    artists, names, platforms = Counter(), {}, Counter()
    ms = 0
    for r in rows:
        a = " ".join((r["_id"].get("a") or "").split())
        if a:
            artists[a] += r["n"]
            names.setdefault(a, r.get("name") or a)
        platforms[r["_id"].get("p") or "UNKNOWN"] += r["n"]
        ms += r["ms"]
    total = sum(artists.values())
    tags = genre_tags(set(artists))
    g = genre_vector(shares(artists, top=200), tags)
    excluded = db.listens.count_documents(
        {"meta.user_id": uid, "played_at": {"$gte": since}, "analytics_allowed": False}
    )
    return {
        **out,
        "plays_30d": total,
        "minutes_30d": round(ms / 60_000),
        "top_artists": [{"name": names[a], "plays": n} for a, n in artists.most_common(5)],
        "genres": [
            {"name": k, "share": round(v, 3)} for k, v in sorted(g.items(), key=lambda x: -x[1])[:5]
        ],
        "platforms": [
            {"platform": p, "share": round(n / total, 3)}
            for p, n in platforms.most_common()
            if total
        ],
        "excluded_note": (
            "Plays from your direct Spotify connection aren't counted in stats."
            if excluded
            else None
        ),
    }


def timeline(uid: str, now: datetime | None = None, months: int = 12) -> list[dict]:
    """JNG-08-03: month by month, what you played most (genres when known, else artists)."""
    now = now or timezone.now()
    db = _db()
    if db is None:
        return []
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    y, m = divmod(first_of_month.year * 12 + first_of_month.month - 1 - (months - 1), 12)
    start = first_of_month.replace(year=y, month=m + 1)
    rows = db.listens.aggregate(
        [
            {"$match": _match(uid, start)},
            {
                "$group": {
                    "_id": {
                        "m": {"$dateToString": {"format": "%Y-%m", "date": "$played_at"}},
                        "a": {"$toLower": "$raw.artist"},
                    },
                    "n": {"$sum": 1},
                    "name": {"$first": "$raw.artist"},
                }
            },
        ]
    )
    per: dict[str, Counter] = defaultdict(Counter)
    names: dict[str, str] = {}
    for r in rows:
        a = " ".join((r["_id"].get("a") or "").split())
        if a:
            per[r["_id"]["m"]][a] += r["n"]
            names.setdefault(a, r.get("name") or a)
    tags = genre_tags({a for c in per.values() for a in c})
    out = []
    cursor = start
    for _ in range(months):
        key = cursor.strftime("%Y-%m")
        c = per.get(key, Counter())
        g = genre_vector(shares(c, top=200), tags) if c else {}
        out.append(
            {
                "month": key,
                "plays": sum(c.values()),
                "top_artist": names[c.most_common(1)[0][0]] if c else None,
                "genres": [
                    {"name": k, "share": round(v, 3)}
                    for k, v in sorted(g.items(), key=lambda x: -x[1])[:3]
                ],
            }
        )
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    return out
