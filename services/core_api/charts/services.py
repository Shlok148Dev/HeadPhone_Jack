"""Song of the Week and Artist of the Week (D-CHART-01..04).

Whose listening: "your people", you plus everyone whose activity you are allowed to see (friends and
circle-mates, through ``core_api.policy``). Blocks, Private mode and visibility settings all apply.

What counts: finished plays only (Mongo ``listens`` holds LISTEN events; now-playing pings live in
Redis), never Spotify Web API data (``analytics_allowed``), never accounts younger than 24 hours.

Scoring rewards breadth over loops: each listener's plays of a song are capped at 3 a day, and a
song's score is the sum over listeners of sqrt(capped plays), so five friends playing once beat one
friend playing twenty times. Artists use the same rule over their songs; featured artists get half
credit. Ties: more listeners, then whoever got there first.

Performance: an hourly job folds new listens into ``DailyPlays`` (one row per listener, local day
and song); a chart is then one indexed query over the viewer's people, cached 15 minutes.
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from .models import ArtistFirstPlay, DailyPlays

DAILY_CAP = 3
MIN_PEOPLE = 3
TOP = 5
FEAT_CREDIT = 0.5
NEW_ACCOUNT_HOURS = 24
CACHE_TTL = 15 * 60
PAST_TTL = 24 * 3600
WATERMARK = "charts:watermark"

# Only unambiguous separators: "&" is not split, so duos ("Simon & Garfunkel") stay one act.
_SPLIT = re.compile(r"\s*(?:,|\s+x\s+|\bfeat\.?\s|\bft\.?\s|\bfeaturing\s|\bwith\s)\s*", re.I)
_TITLE_FEAT = re.compile(r"[\(\[]\s*(?:feat\.?|ft\.?|featuring|with)\s+([^\)\]]+)[\)\]]", re.I)


def _keys():
    from artwork.services import artist_key, track_key

    return artist_key, track_key


def split_artists(credit: str, title: str = "") -> list[list]:
    """[[artist_key, name, credit]]: the first credited act 1.0, everyone featured 0.5."""
    artist_key, _ = _keys()
    names = [n.strip() for n in _SPLIT.split(credit or "") if n and n.strip()]
    for m in _TITLE_FEAT.findall(title or ""):
        names += [n.strip() for n in re.split(r",|&", m) if n.strip()]
    out: list[list] = []
    seen: set[str] = set()
    for i, n in enumerate(names):
        k = artist_key(n)
        if k and k not in seen:
            seen.add(k)
            out.append([k, n, 1.0 if i == 0 else FEAT_CREDIT])
    return out


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _aware(dt) -> datetime:
    if isinstance(dt, datetime):
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    return timezone.now()


# ---- write side: fold listens into DailyPlays ---------------------------------------------


def refresh_user(
    user, since: date | None = None, now: datetime | None = None, full: bool = False
) -> int:
    """Rebuild this user's rows from ``since`` (default: start of last week, local) to now."""
    from core_api.mongo import get_db
    from drops.services import tz_of

    db = get_db()
    if db is None:
        return 0
    _, track_key = _keys()
    tz = tz_of(user)
    now = now or timezone.now()
    since = since or (week_start(now.astimezone(tz).date()) - timedelta(days=7))
    start = datetime.combine(since, time.min, tzinfo=tz).astimezone(UTC)
    query: dict = {"meta.user_id": str(user.pk), "analytics_allowed": {"$ne": False}}
    if not full:
        query["played_at"] = {"$gte": start}
    rows: dict[tuple, dict] = {}
    first_play: dict[str, datetime] = {}
    for doc in db.listens.find(query, {"raw": 1, "played_at": 1, "recording_id": 1}):
        raw = doc.get("raw") or {}
        title, artist = (raw.get("title") or "").strip(), (raw.get("artist") or "").strip()
        if not title or not artist:
            continue
        at = _aware(doc.get("played_at"))
        credits = split_artists(artist, title)
        for k, _n, _c in credits:
            if k not in first_play or at < first_play[k]:
                first_play[k] = at
        day = at.astimezone(tz).date()
        if day < since:
            continue  # full scans feed first-play only; rows stay within the window
        key = (day, track_key(title, artist))
        r = rows.get(key)
        if r is None:
            rows[key] = {
                "title": title,
                "artist": artist,
                "artists": credits,
                "recording_id": doc.get("recording_id"),
                "plays": 1,
                "first_at": at,
            }
        else:
            r["plays"] += 1
            r["first_at"] = min(r["first_at"], at)
            r["recording_id"] = r["recording_id"] or doc.get("recording_id")
    with transaction.atomic():
        DailyPlays.objects.filter(user=user, day__gte=since).delete()
        DailyPlays.objects.bulk_create(
            [
                DailyPlays(
                    user=user,
                    day=day,
                    track_key=tk,
                    **{**r, "recording_id": r["recording_id"] or None},
                )
                for (day, tk), r in rows.items()
            ]
        )
        existing = {
            a.artist_key: a
            for a in ArtistFirstPlay.objects.filter(user=user, artist_key__in=list(first_play))
        }
        new, changed = [], []
        for k, at in first_play.items():
            a = existing.get(k)
            if a is None:
                new.append(ArtistFirstPlay(user=user, artist_key=k, first_at=at))
            elif at < a.first_at:
                a.first_at = at
                changed.append(a)
        ArtistFirstPlay.objects.bulk_create(new, ignore_conflicts=True)
        if changed:
            ArtistFirstPlay.objects.bulk_update(changed, ["first_at"])
    return len(rows)


def refresh_active(now: datetime | None = None) -> int:
    """Hourly: rebuild everyone whose listens arrived since the last run (by observed time)."""
    from accounts.models import User
    from core_api.mongo import get_db
    from core_api.redis_client import get_redis

    db, r = get_db(), get_redis()
    if db is None:
        return 0
    now = now or timezone.now()
    raw = r.get(WATERMARK)
    mark = datetime.fromisoformat(raw) if raw else now - timedelta(days=14)
    since = mark - timedelta(minutes=10)  # overlap: late writes are not missed
    ids = db.listens.distinct(
        "meta.user_id", {"$or": [{"observed_at": {"$gte": since}}, {"played_at": {"$gte": since}}]}
    )
    n = 0
    for u in User.objects.filter(
        pk__in=[i for i in ids if i], is_active=True, deleted_at__isnull=True
    ):
        refresh_user(u, now=now, full=raw is None)  # first ever run also backfills first plays
        n += 1
    r.set(WATERMARK, now.isoformat())
    if n:
        invalidate()  # once per run: charts change hourly anyway
    return n


# ---- read side: the charts ----------------------------------------------------------------


def _people(viewer, now: datetime) -> list:
    """You plus everyone whose activity you may see, minus blocks and brand-new accounts."""
    from accounts.models import User
    from circles.models import CircleMember
    from core_api import policy
    from social.services import blocked_ids, friend_ids

    mine = CircleMember.objects.filter(user=viewer).values("circle_id")
    mates = CircleMember.objects.filter(circle_id__in=mine).values_list("user_id", flat=True)
    ids = (set(friend_ids(viewer.pk)) | set(mates) | {viewer.pk}) - blocked_ids(viewer.pk)
    cutoff = now - timedelta(hours=NEW_ACCOUNT_HOURS)
    users = list(
        User.objects.filter(
            pk__in=ids, is_active=True, deleted_at__isnull=True, date_joined__lte=cutoff
        )
    )
    with policy.bulk(viewer, users):
        return [u for u in users if u.pk == viewer.pk or policy.can_view_activity(viewer, u, now)]


def _rank(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """(songs, artists), each scored, ranked and trimmed to TOP, with per-entry detail."""
    capped: dict[tuple, int] = defaultdict(int)  # (track_key, user) -> capped plays this week
    first: dict[tuple, datetime] = {}
    meta: dict[str, dict] = {}
    for r in rows:
        k = (r["track_key"], r["user_id"])
        capped[k] += min(r["plays"], DAILY_CAP)
        first[k] = min(first.get(k, r["first_at"]), r["first_at"])
        m = meta.setdefault(
            r["track_key"],
            {
                "title": r["title"],
                "artist": r["artist"],
                "artists": r["artists"],
                "recording_id": r["recording_id"],
            },
        )
        m["recording_id"] = m["recording_id"] or r["recording_id"]

    songs: dict[str, dict] = {}
    by_artist: dict[str, dict] = {}
    for (tk, uid), c in capped.items():
        s = songs.setdefault(
            tk, {"key": tk, **meta[tk], "score": 0.0, "plays": 0, "listeners": {}, "first": None}
        )
        s["score"] += math.sqrt(c)
        s["plays"] += c
        s["listeners"][uid] = c
        if s["first"] is None or first[(tk, uid)] < s["first"][1]:
            s["first"] = (uid, first[(tk, uid)])
        for ak, name, credit in meta[tk]["artists"]:
            a = by_artist.setdefault(
                ak,
                {
                    "key": ak,
                    "name": name,
                    "per_user": defaultdict(float),
                    "songs": defaultdict(float),
                },
            )
            if credit == 1.0:
                a["name"] = name  # prefer the spelling used when they're the lead act
            a["per_user"][uid] += c * credit
            a["songs"][tk] += c * credit

    def order(e):  # breadth first, then reach, then who got there first
        return (
            -round(e["score"], 6),
            -len(e["listeners"]),
            e["first"][1] if e.get("first") else datetime.max.replace(tzinfo=UTC),
        )

    top_songs = sorted(songs.values(), key=order)[:TOP]
    artists = []
    for a in by_artist.values():
        a["score"] = sum(math.sqrt(v) for v in a["per_user"].values())
        a["listeners"] = dict(a["per_user"])
        a["plays"] = sum(a["per_user"].values())
        a["first"] = None
        a["top_song"] = max(a["songs"].items(), key=lambda kv: kv[1])[0]
        artists.append(a)
    top_artists = sorted(artists, key=order)[:TOP]
    return top_songs, top_artists


def _chart(viewer, ws: date, now: datetime) -> dict:
    people = _people(viewer, now)
    ids = [u.pk for u in people]
    rows = list(
        DailyPlays.objects.filter(
            user_id__in=ids, day__gte=ws, day__lt=ws + timedelta(days=7)
        ).values(
            "user_id",
            "track_key",
            "title",
            "artist",
            "artists",
            "recording_id",
            "plays",
            "first_at",
        )
    )
    contributing = {r["user_id"] for r in rows}
    songs, artists = _rank(rows)
    return {
        "people": people,
        "contributing": len(contributing),
        "songs": songs,
        "artists": artists,
        "song_meta": {r["track_key"]: r for r in rows},
    }


def weekly(viewer, ws: date | None = None, now: datetime | None = None) -> dict:
    """The viewer's weekly charts (cached). ``ws`` defaults to this week (viewer's timezone)."""
    from core_api.redis_client import get_redis
    from drops.services import tz_of

    now = now or timezone.now()
    this_ws = week_start(now.astimezone(tz_of(viewer)).date())
    ws = ws or this_ws
    key = f"charts:v1:{viewer.pk}:{ws.isoformat()}"
    r = get_redis()
    hit = r.get(key)
    if hit:
        return json.loads(hit)
    data = _build(viewer, ws, now, this_ws)
    r.setex(key, CACHE_TTL if ws >= this_ws else PAST_TTL, json.dumps(data, default=str))
    return data


def _build(viewer, ws: date, now: datetime, this_ws: date) -> dict:
    from artwork.services import enrich, enrich_artists
    from drops.services import tz_of
    from feed.resolver import _links, _search_links
    from social.views import person

    cur = _chart(viewer, ws, now)
    prev = _chart(viewer, ws - timedelta(days=7), now)
    prev_song = {s["key"]: i + 1 for i, s in enumerate(prev["songs"])}
    prev_artist = {a["key"]: i + 1 for i, a in enumerate(prev["artists"])}
    users = {u.pk: u for u in cur["people"]}

    def who(listeners: dict) -> list:
        ranked = sorted(listeners.items(), key=lambda kv: -kv[1])
        return [
            person(users[uid], "self" if uid == viewer.pk else "friends")
            for uid, _ in ranked[:5]
            if uid in users
        ]

    def move(rank: int, before: dict, key: str) -> dict:
        if key not in before:
            return {"kind": "new", "by": 0}
        d = before[key] - rank
        return {"kind": "up" if d > 0 else "down" if d < 0 else "same", "by": abs(d)}

    songs = []
    for i, s in enumerate(cur["songs"], start=1):
        rid = str(s["recording_id"]) if s["recording_id"] else None
        found = s["first"]
        songs.append(
            {
                "rank": i,
                "title": s["title"],
                "artist": s["artist"],
                "recording_id": rid,
                "listeners": len(s["listeners"]),
                "plays": s["plays"],
                "movement": move(i, prev_song, s["key"]),
                "people": who(s["listeners"]),
                "found_first": person(
                    users[found[0]], "self" if found[0] == viewer.pk else "friends"
                )
                if found and len(s["listeners"]) >= 2 and found[0] in users
                else None,
                "you_played": viewer.pk in s["listeners"],
                "links": _links(rid),
                "search_links": _search_links(s["title"], s["artist"]),
            }
        )
    enrich(songs)

    window = (
        datetime.combine(ws, time.min, tzinfo=UTC)
        - timedelta(days=1),  # generous edges; refined per fan below
        datetime.combine(ws + timedelta(days=7), time.min, tzinfo=UTC) + timedelta(days=1),
    )
    fans = defaultdict(set)
    for f in ArtistFirstPlay.objects.filter(
        artist_key__in=[a["key"] for a in cur["artists"]],
        user_id__in=list(users),
        first_at__gte=window[0],
        first_at__lt=window[1],
    ):
        local = f.first_at.astimezone(tz_of(users[f.user_id])).date()
        if ws <= local < ws + timedelta(days=7):
            fans[f.artist_key].add(f.user_id)

    artists = []
    for i, a in enumerate(cur["artists"], start=1):
        top = cur["song_meta"].get(a["top_song"], {})
        top_song = {
            "title": top.get("title"),
            "artist": top.get("artist"),
            "recording_id": str(top["recording_id"]) if top.get("recording_id") else None,
        }
        top_song["links"] = _links(top_song["recording_id"])
        top_song["search_links"] = _search_links(top_song["title"] or "", top_song["artist"] or "")
        artists.append(
            {
                "rank": i,
                "name": a["name"],
                "listeners": len(a["listeners"]),
                "plays": round(a["plays"]),
                "movement": move(i, prev_artist, a["key"]),
                "people": who(a["listeners"]),
                "new_fans": [
                    person(users[u], "self" if u == viewer.pk else "friends")
                    for u in list(fans[a["key"]])[:5]
                ],
                "you_listened": viewer.pk in a["listeners"],
                "top_song": top_song,
            }
        )
    enrich_artists(artists)
    enrich([a["top_song"] for a in artists])
    from core_api.redis_client import get_redis

    mark = get_redis().get(WATERMARK)
    return {
        "week_start": ws.isoformat(),
        "week_end": (ws + timedelta(days=6)).isoformat(),
        "is_current": ws >= this_ws,
        "updated_at": mark,
        "contributors": cur["contributing"],
        "enough": cur["contributing"] >= MIN_PEOPLE,
        "songs": songs,
        "artists": artists,
    }


def invalidate(user_id=None) -> None:
    """Drop cached charts (after new plays or a friendship change). Pilot scale: all keys."""
    from core_api.redis_client import get_redis

    r = get_redis()
    keys = list(r.scan_iter("charts:v1:*"))
    if keys:
        r.delete(*keys)  # small keyspace at pilot scale; per-viewer fan-out is a Phase-3 refinement
