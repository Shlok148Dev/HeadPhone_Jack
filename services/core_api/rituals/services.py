"""Battle and recap rules (EP-09). Times follow each circle's schedule in IST (Tech Bible 7.4)."""

from __future__ import annotations

import logging
import secrets
from collections import Counter
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from circles.models import Circle, CircleMember, Role
from core_api.errors import ApiError

from .models import SEASON_WEEKS, VOTES_PER_WEEK, Battle, BattleVote, Nomination, Recap

log = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")
DAYS = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}
DEFAULT = {"nominate": "MON 18:00", "vote": "FRI 18:00", "close": "SUN 21:00"}


def week_of(now: datetime) -> date:
    local = now.astimezone(IST)
    return (local - timedelta(days=local.weekday())).date()


def _at(week: date, spec: str) -> datetime:
    day, hm = (spec or "").split(" ")
    h, m = (int(x) for x in hm.split(":"))
    d = week + timedelta(days=DAYS[day.upper()])
    return datetime(d.year, d.month, d.day, h, m, tzinfo=IST)


def _times(circle: Circle, week: date) -> tuple[datetime, datetime, datetime]:
    sched = {**DEFAULT, **{k: v for k, v in (circle.battle_schedule or {}).items() if v}}
    try:
        times = tuple(_at(week, sched[k]) for k in ("nominate", "vote", "close"))
    except (KeyError, ValueError):
        times = tuple(_at(week, DEFAULT[k]) for k in ("nominate", "vote", "close"))
    if not times[0] < times[1] < times[2]:
        times = tuple(_at(week, DEFAULT[k]) for k in ("nominate", "vote", "close"))
    return times  # type: ignore[return-value]


def battle_for(circle: Circle, now: datetime | None = None) -> Battle:
    """The battle people should see now: this week's, or last week's results until this week's
    nominations open."""
    now = now or timezone.now()
    week = week_of(now)
    nominate, vote, close = _times(circle, week)
    if now < nominate:
        prev = Battle.objects.filter(circle=circle, week=week - timedelta(days=7)).first()
        if prev is not None:
            return prev
    b, created = Battle.objects.get_or_create(
        circle=circle,
        week=week,
        defaults={"nominate_opens": nominate, "vote_opens": vote, "closes_at": close},
    )
    if created and (circle.battle_schedule or {}).get("skip_week") == week.isoformat():
        b.skipped = True
        b.save(update_fields=["skipped"])
    return b


def phase(b: Battle, now: datetime | None = None) -> str:
    now = now or timezone.now()
    if b.skipped:
        return "skipped"
    if b.results is not None or now >= b.closes_at:
        return "closed"
    if now >= b.vote_opens:
        return "voting"
    if now >= b.nominate_opens:
        return "nominating"
    return "upcoming"


def require_member(circle_id, user) -> tuple[Circle, CircleMember]:
    m = CircleMember.objects.select_related("circle").filter(circle_id=circle_id, user=user).first()
    if m is None:
        raise ApiError("NOT_FOUND", "We couldn't find that circle.", 404)
    return m.circle, m


@transaction.atomic
def nominate(b: Battle, user, song: dict, now: datetime | None = None) -> Nomination:
    """JNG-09-02: one nomination per person per week (changeable until voting opens)."""
    from sources.models import Recording

    if phase(b, now) != "nominating":
        raise ApiError("NOMINATIONS_CLOSED", "Nominations are closed for this week.", 409)
    rec = None
    if song.get("recording_id"):
        rec = Recording.objects.filter(pk=song["recording_id"]).first()
    title = (rec.title if rec else str(song.get("title") or "")).strip()[:500]
    artist = (rec.artist_name if rec else str(song.get("artist") or "")).strip()[:500]
    if not title or not artist:
        raise ApiError("VALIDATION_ERROR", "Pick a song to nominate.", 400)
    n, _ = Nomination.objects.update_or_create(
        battle=b, user=user, defaults={"recording": rec, "title": title, "artist": artist}
    )
    return n


@transaction.atomic
def vote(b: Battle, user, nomination_id, now: datetime | None = None) -> BattleVote:
    """JNG-09-02: 3 votes a week, never on your own song; late votes are refused (Gherkin)."""
    now = now or timezone.now()
    b = Battle.objects.select_for_update().get(pk=b.pk)  # serialises one voter's 3-vote budget
    p = phase(b, now)
    if p == "closed":
        raise ApiError("VOTING_CLOSED", "Voting has closed", 409)
    if p != "voting":
        raise ApiError("VOTING_NOT_OPEN", "Voting hasn't opened yet.", 409)
    n = b.nominations.filter(pk=nomination_id).first()
    if n is None:
        raise ApiError("NOT_FOUND", "That nomination isn't in this battle.", 404)
    if n.user_id == user.pk:
        raise ApiError("OWN_NOMINATION", "You can't vote for your own song.", 400)
    existing = BattleVote.objects.filter(nomination=n, voter=user).first()
    if existing:
        return existing
    if BattleVote.objects.filter(battle=b, voter=user).count() >= VOTES_PER_WEEK:
        raise ApiError("NO_VOTES_LEFT", f"You've used your {VOTES_PER_WEEK} votes this week.", 409)
    return BattleVote.objects.create(battle=b, nomination=n, voter=user)


def unvote(b: Battle, user, nomination_id, now: datetime | None = None) -> None:
    if phase(b, now) != "voting":
        raise ApiError("VOTING_CLOSED", "Voting has closed", 409)
    BattleVote.objects.filter(battle=b, voter=user, nomination_id=nomination_id).delete()


def leaderboard(b: Battle) -> list[dict]:
    counts = Counter(b.votes.values_list("nomination_id", flat=True))
    noms = sorted(b.nominations.select_related("user"), key=lambda n: (-counts[n.pk], n.created_at))
    out, rank, last = [], 0, None
    for i, n in enumerate(noms):
        if counts[n.pk] != last:
            rank, last = i + 1, counts[n.pk]
        out.append(
            {
                "nomination_id": str(n.pk),
                "rank": rank,
                "votes": counts[n.pk],
                "title": n.title,
                "artist": n.artist,
                "recording_id": str(n.recording_id) if n.recording_id else None,
                "user": {
                    "id": str(n.user_id),
                    "username": n.user.username,
                    "display_name": n.user.display_name or n.user.username,
                },
            }
        )
    return out


def close_due(now: datetime | None = None) -> int:
    """Every minute: publish results for battles whose voting closed (JNG-09-03, ≤ 5 min)."""
    from notifications.services import notify

    now = now or timezone.now()
    closed = 0
    for b in Battle.objects.filter(
        results__isnull=True, skipped=False, closes_at__lte=now
    ).select_related("circle"):
        with transaction.atomic():
            b = Battle.objects.select_for_update().get(pk=b.pk)
            if b.results is not None:
                continue
            b.results = leaderboard(b)
            b.closed_at = now
            b.save(update_fields=["results", "closed_at"])
        closed += 1
        if b.results:
            for uid in CircleMember.objects.filter(circle_id=b.circle_id).values_list(
                "user_id", flat=True
            ):
                notify(uid, "battle", f"{b.circle.name}: battle results are in", url="/rituals")
    return closed


def skip_week(circle: Circle, member: CircleMember, now: datetime | None = None) -> Battle:
    """JNG-09-08: an admin skips this week; the season just counts the weeks that ran."""
    if member.role not in (Role.OWNER, Role.ADMIN):
        raise ApiError("FORBIDDEN", "Only the circle's admins can skip a week.", 403)
    b = battle_for(circle, now)
    if b.results is not None:
        raise ApiError("ALREADY_CLOSED", "This week's battle has already finished.", 409)
    b.skipped = True
    b.save(update_fields=["skipped"])
    return b


def season(circle: Circle) -> dict:
    """JNG-09-04: wins over the last 8 battles that actually ran."""
    weeks = list(
        Battle.objects.filter(circle=circle, skipped=False, results__isnull=False).order_by(
            "-week"
        )[:SEASON_WEEKS]
    )
    wins: Counter = Counter()
    names: dict[str, dict] = {}
    for b in weeks:
        for row in b.results or []:
            names[row["user"]["id"]] = row["user"]
            if row["rank"] == 1 and row["votes"] > 0:
                wins[row["user"]["id"]] += 1
    table = [{"user": names[u], "wins": n} for u, n in wins.most_common()]
    return {"weeks": len(weeks), "of": SEASON_WEEKS, "table": table}


# ---- monthly recap (JNG-09-05/06) ----------------------------------------------------------


def _month_bounds(month: str) -> tuple[datetime, datetime]:
    y, m = (int(x) for x in month.split("-"))
    start = datetime(y, m, 1, tzinfo=IST)
    end = datetime(y + (m == 12), m % 12 + 1, 1, tzinfo=IST)
    return start, end


def build_recap(user, month: str) -> dict | None:
    """Facts only from analysable listens and Jingle-native activity."""
    from core_api.mongo import get_db
    from sends.models import Delivery, Recommendation

    db = get_db()
    if db is None:
        return None
    start, end = _month_bounds(month)
    match = {
        "meta.user_id": str(user.pk),
        "played_at": {"$gte": start, "$lt": end},
        "analytics_allowed": {"$ne": False},
    }
    rows = list(
        db.listens.aggregate(
            [
                {"$match": match},
                {
                    "$group": {
                        "_id": {"a": "$raw.artist", "t": "$raw.title"},
                        "n": {"$sum": 1},
                        "ms": {"$sum": {"$ifNull": ["$raw.duration_ms", 210_000]}},
                    }
                },
            ]
        )
    )
    if not rows:
        return None
    artists: Counter = Counter()
    tracks: Counter = Counter()
    ms = 0
    for r in rows:
        a, t = r["_id"].get("a") or "", r["_id"].get("t") or ""
        artists[a] += r["n"]
        tracks[(t, a)] += r["n"]
        ms += r["ms"]
    from insights.compute import genre_tags, genre_vector, shares

    g = genre_vector(
        shares(Counter({k.lower(): v for k, v in artists.items()}), top=200),
        genre_tags({a.lower() for a in artists}),
    )
    wins = sum(
        1
        for b in Battle.objects.filter(
            closes_at__gte=start, closes_at__lt=end, results__isnull=False
        )
        for row in (b.results or [])
        if row["rank"] == 1 and row["votes"] > 0 and row["user"]["id"] == str(user.pk)
    )
    return {
        "month": month,
        "minutes": round(ms / 60_000),
        "plays": sum(artists.values()),
        "top_artists": [{"name": a, "plays": n} for a, n in artists.most_common(5)],
        "top_tracks": [
            {"title": t, "artist": a, "plays": n} for (t, a), n in tracks.most_common(5)
        ],
        "top_genre": max(g, key=g.get) if g else None,
        "sends": Recommendation.objects.filter(
            sender=user, created_at__gte=start, created_at__lt=end
        ).count(),
        "received": Delivery.objects.filter(
            recipient=user, rec__created_at__gte=start, rec__created_at__lt=end
        ).count(),
        "battle_wins": wins,
    }


def previous_month(now: datetime | None = None) -> str:
    local = (now or timezone.now()).astimezone(IST)
    first = local.replace(day=1)
    last = first - timedelta(days=1)
    return last.strftime("%Y-%m")


def make_recaps(now: datetime | None = None) -> int:
    """Daily on the 1st and 2nd (well inside 48 h): last month's recap for everyone who played."""
    from accounts.models import User
    from notifications.services import notify

    month = previous_month(now)
    made = 0
    for u in User.objects.filter(is_active=True, deleted_at__isnull=True).exclude(
        recaps__month=month
    ):
        try:
            data = build_recap(u, month)
        except Exception:  # noqa: BLE001
            log.warning("recap failed for a user")
            continue
        if data is None:
            continue
        Recap.objects.get_or_create(user=u, month=month, defaults={"data": data})
        notify(u.pk, "recap", "Your monthly recap is ready", url="/rituals#recap")
        made += 1
    return made


def share(recap: Recap, on: bool) -> Recap:
    recap.share_token = secrets.token_urlsafe(12) if on else None
    recap.save(update_fields=["share_token"])
    return recap
