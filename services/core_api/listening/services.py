"""Live session rules (JNG-07-05…09). Every change bumps ``sess:{id}:ver`` and broadcasts the
room's public state, so every participant converges on the same order (Tech Bible 4.3)."""

from __future__ import annotations

import json
import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from accounts.models import User
from circles.models import CircleMember
from core_api import events, policy
from core_api.errors import ApiError
from core_api.redis_client import get_redis

from .models import MAX_PARTICIPANTS, MAX_QUEUE, ListeningSession, Participant, QueueEntry, Vote

log = logging.getLogger(__name__)
PRESENCE_TTL = 60  # refreshed by the realtime gateway every 20 s while the room is open
IDLE_END = timedelta(minutes=10)


def _presence_key(sid, uid) -> str:
    return f"sesspres:{sid}:{uid}"


def present_ids(s: ListeningSession) -> set[str]:
    try:
        r = get_redis()
        ids = [
            str(p.user_id)
            for p in s.participants.filter(left_at__isnull=True, joined_at__isnull=False)
        ]
        vals = r.mget([_presence_key(s.pk, u) for u in ids]) if ids else []
        return {u for u, v in zip(ids, vals, strict=False) if v}
    except Exception:  # noqa: BLE001 - presence is best effort
        return set()


def _next_version(s: ListeningSession) -> int:
    try:
        return int(get_redis().incr(f"sess:{s.pk}:ver"))
    except Exception:  # noqa: BLE001
        return int(timezone.now().timestamp() * 1000)


def current_version(s: ListeningSession) -> int:
    try:
        return int(get_redis().get(f"sess:{s.pk}:ver") or 0)
    except Exception:  # noqa: BLE001
        return 0


def ordered_queue(s: ListeningSession):
    return s.queue.filter(played_at__isnull=True).order_by("-score", "created_at")


def _person(u: User | None) -> dict | None:
    if u is None:
        return None
    return {"id": str(u.pk), "username": u.username, "display_name": u.display_name or u.username}


def _entry(e: QueueEntry) -> dict:
    return {
        "id": str(e.pk),
        "recording_id": str(e.recording_id) if e.recording_id else None,
        "title": e.title,
        "artist": e.artist,
        "added_by": _person(e.added_by),
        "score": e.score,
    }


def public_state(s: ListeningSession) -> dict:
    """What every participant sees: no per-viewer data, never who added an anonymous entry."""
    s.refresh_from_db()
    parts = s.participants.filter(left_at__isnull=True, joined_at__isnull=False).select_related(
        "user"
    )
    online = present_ids(s)
    return {
        "id": str(s.pk),
        "title": s.title,
        "host": _person(s.host),
        "ended": s.ended_at is not None,
        "now_playing": _entry(s.now_playing) if s.now_playing_id else None,
        "queue": [_entry(e) for e in ordered_queue(s).select_related("added_by")[:MAX_QUEUE]],
        "participants": [
            {**_person(p.user), "online": str(p.user_id) in online}
            for p in parts.order_by("joined_at")
        ],
    }


def broadcast(s: ListeningSession) -> int:
    version = _next_version(s)
    state = public_state(s)

    def send():
        events.publish_domain(
            "queue.delta",
            {"session_id": str(s.pk), "version": version, "state": json.dumps(state, default=str)},
        )

    transaction.on_commit(send)
    return version


def get_active(session_id) -> ListeningSession:
    s = (
        ListeningSession.objects.select_related("host")
        .filter(pk=session_id, ended_at__isnull=True)
        .first()
    )
    if s is None:
        raise ApiError("NOT_FOUND", "This session has ended.", 404)
    return s


def may_join(s: ListeningSession, user) -> bool:
    if s.ended_at is not None:
        return False
    if policy.is_blocked_either_way(user, s.host_id):
        return False
    if s.participants.filter(user=user).exists():
        return True
    return bool(
        s.circle_id and CircleMember.objects.filter(circle_id=s.circle_id, user=user).exists()
    )


def require_participant(s: ListeningSession, user) -> Participant:
    p = s.participants.filter(user=user, joined_at__isnull=False, left_at__isnull=True).first()
    if p is None:
        raise ApiError("NOT_FOUND", "Join the session first.", 404)
    return p


@transaction.atomic
def start(host, title: str = "", user_ids=(), circle_id=None) -> ListeningSession:
    """JNG-07-05: host starts a room and invites friends or a circle."""
    circle = None
    if circle_id:
        from circles.models import Circle

        if not CircleMember.objects.filter(circle_id=circle_id, user=host).exists():
            raise ApiError("NOT_FOUND", "We couldn't find that circle.", 404)
        circle = Circle.objects.get(pk=circle_id)
    invitees = []
    for uid in user_ids:
        if not policy.are_friends(host, uid):
            raise ApiError("NOT_FOUND", "You can invite friends or a circle.", 404)
        invitees.append(str(uid))
    if len(invitees) >= MAX_PARTICIPANTS:
        raise ApiError("VALIDATION_ERROR", f"Sessions hold up to {MAX_PARTICIPANTS} people.", 400)
    name = (title or "").strip()[:80] or (
        f"{circle.name} session"
        if circle
        else f"{(host.display_name or host.username).split(' ')[0]}'s session"
    )
    s = ListeningSession.objects.create(title=name, host=host, circle=circle)
    now = timezone.now()
    Participant.objects.create(session=s, user=host, invited=True, joined_at=now)
    Participant.objects.bulk_create(
        Participant(session=s, user_id=u, invited=True) for u in invitees
    )
    notify = set(invitees)
    if circle:
        notify |= {
            str(u)
            for u in CircleMember.objects.filter(circle=circle).values_list("user_id", flat=True)
        }
    notify.discard(str(host.pk))
    for uid in notify:
        transaction.on_commit(
            lambda uid=uid: events.publish_domain(
                "notify", {"user_id": uid, "type": "session_invite", "id": str(s.pk)}
            )
        )
    broadcast(s)
    return s


@transaction.atomic
def join(s: ListeningSession, user) -> Participant:
    if not may_join(s, user):
        raise ApiError("NOT_FOUND", "This session has ended.", 404)
    p, _ = Participant.objects.get_or_create(session=s, user=user)
    if p.joined_at is None or p.left_at is not None:
        if (
            s.participants.filter(joined_at__isnull=False, left_at__isnull=True).count()
            >= MAX_PARTICIPANTS
        ):
            raise ApiError("SESSION_FULL", "This session is full.", 409)
        p.joined_at, p.left_at = timezone.now(), None
        p.save(update_fields=["joined_at", "left_at"])
        broadcast(s)
    return p


def _hand_over(s: ListeningSession, exclude=None) -> bool:
    """JNG-07-08: the longest-present online participant becomes host, else anyone still in."""
    rest = s.participants.filter(joined_at__isnull=False, left_at__isnull=True).exclude(
        user_id=exclude
    )
    online = present_ids(s)
    nxt = next((p for p in rest.order_by("joined_at") if str(p.user_id) in online), None)
    nxt = nxt or rest.order_by("joined_at").first()
    if nxt is None:
        s.ended_at = timezone.now()
        s.save(update_fields=["ended_at"])
        return False
    s.host_id = nxt.user_id
    s.save(update_fields=["host"])
    return True


@transaction.atomic
def leave(s: ListeningSession, user) -> None:
    p = require_participant(s, user)
    p.left_at = timezone.now()
    p.save(update_fields=["left_at"])
    if s.host_id == user.pk:
        _hand_over(s, exclude=user.pk)
    broadcast(s)


@transaction.atomic
def add(s: ListeningSession, user, item: dict, anonymous: bool, key: str) -> QueueEntry:
    """JNG-07-06: add to the shared queue, optionally anonymously. Idempotent per key."""
    from sources.models import Recording

    require_participant(s, user)
    key = (key or "").strip()[:64]
    if not key:
        raise ApiError("VALIDATION_ERROR", "An idempotency key is required.", 400)
    existing = s.queue.filter(idempotency_key=key).first()
    if existing:
        return existing
    if ordered_queue(s).count() >= MAX_QUEUE:
        raise ApiError("QUEUE_FULL", "The queue is full. Vote some songs through first.", 409)
    rec = None
    if item.get("recording_id"):
        rec = Recording.objects.filter(pk=item["recording_id"]).first()
        if rec is None:
            raise ApiError("VALIDATION_ERROR", "We couldn't find that song.", 400)
    title = (rec.title if rec else str(item.get("title") or "")).strip()[:500]
    artist = (rec.artist_name if rec else str(item.get("artist") or "")).strip()[:500]
    if not title or not artist:
        raise ApiError("VALIDATION_ERROR", "Add a song with a title and an artist.", 400)
    e = QueueEntry.objects.create(
        session=s,
        recording=rec,
        title=title,
        artist=artist,
        added_by=None if anonymous else user,
        submitted_by=user,
        idempotency_key=key,
    )
    broadcast(s)
    return e


@transaction.atomic
def vote(entry_id, user, value: int) -> QueueEntry:
    """JNG-07-07: one ±1 vote per person per entry (0 withdraws). The row lock makes concurrent
    votes all count."""
    if value not in (1, -1, 0):
        raise ApiError("VALIDATION_ERROR", "Vote up (1) or down (-1).", 400)
    e = QueueEntry.objects.select_for_update().select_related("session").filter(pk=entry_id).first()
    if e is None or e.played_at is not None or e.session.ended_at is not None:
        raise ApiError("NOT_FOUND", "That song isn't in the queue any more.", 404)
    require_participant(e.session, user)
    if value == 0:
        Vote.objects.filter(entry=e, user=user).delete()
    else:
        Vote.objects.update_or_create(entry=e, user=user, defaults={"value": value})
    e.score = Vote.objects.filter(entry=e).aggregate(s=Sum("value"))["s"] or 0
    e.save(update_fields=["score"])
    broadcast(e.session)
    return e


@transaction.atomic
def next_track(s: ListeningSession, user) -> ListeningSession:
    if s.host_id != user.pk:
        raise ApiError("FORBIDDEN", "Only the host moves the queue on.", 403)
    now = timezone.now()
    top = ordered_queue(s).first()
    if top:
        top.played_at = now
        top.save(update_fields=["played_at"])
    s.now_playing = top
    s.save(update_fields=["now_playing"])
    broadcast(s)
    return s


@transaction.atomic
def end(s: ListeningSession, user) -> None:
    if s.host_id != user.pk:
        raise ApiError("FORBIDDEN", "Only the host can end the session.", 403)
    s.ended_at = timezone.now()
    s.save(update_fields=["ended_at"])
    broadcast(s)


def my_votes(s: ListeningSession, user) -> dict[str, int]:
    return {
        str(v.entry_id): v.value
        for v in Vote.objects.filter(entry__session=s, entry__played_at__isnull=True, user=user)
    }


def sweep(now=None) -> dict:
    """Every 30 s: a host who dropped off hands over; a room nobody is in for 10 min ends."""
    now = now or timezone.now()
    handed = ended = 0
    for s in ListeningSession.objects.filter(ended_at__isnull=True):
        online = present_ids(s)
        if online and str(s.host_id) not in online:
            with transaction.atomic():
                if _hand_over(s, exclude=s.host_id):
                    handed += 1
                broadcast(s)
        elif not online and s.created_at < now - IDLE_END:
            last = s.queue.order_by("-created_at").values_list("created_at", flat=True).first()
            if (last or s.created_at) < now - IDLE_END:
                with transaction.atomic():
                    s.ended_at = now
                    s.save(update_fields=["ended_at"])
                    broadcast(s)
                ended += 1
    return {"handed_over": handed, "ended": ended}
