"""Blend rules (EP-07). A member's plays shape a Blend only if every other member may see them."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import User
from circles.models import CircleMember
from core_api import policy
from core_api.errors import ApiError

from . import engine
from .models import Blend, BlendMember, BlendTrack

log = logging.getLogger(__name__)
WINDOW_DAYS = 90


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def contributors(members: list[User]) -> set[str]:
    """Members whose listening every other member may see (BR-06/07, Private mode, visibility)."""
    return {
        str(m.pk)
        for m in members
        if all(policy.can_view_activity(o, m) for o in members if o.pk != m.pk)
    }


def load_plays(user_ids: list[str]) -> tuple[dict[str, Counter], dict[str, engine.Track]]:
    """Per-user play counts over 90 days, analysable listens only (never direct-Spotify data)."""
    from core_api.mongo import get_db

    db = get_db()
    plays: dict[str, Counter] = defaultdict(Counter)
    catalog: dict[str, engine.Track] = {}
    if db is None or not user_ids:
        return plays, catalog
    since = timezone.now() - timedelta(days=WINDOW_DAYS)
    rows = db.listens.aggregate(
        [
            {
                "$match": {
                    "meta.user_id": {"$in": user_ids},
                    "played_at": {"$gte": since},
                    "analytics_allowed": {"$ne": False},
                }
            },
            {
                "$group": {
                    "_id": {
                        "u": "$meta.user_id",
                        "r": "$recording_id",
                        "a": {"$toLower": "$raw.artist"},
                        "t": {"$toLower": "$raw.title"},
                    },
                    "n": {"$sum": 1},
                    "artist": {"$first": "$raw.artist"},
                    "title": {"$first": "$raw.title"},
                }
            },
        ]
    )
    for r in rows:
        g = r["_id"]
        if not r.get("title") or not r.get("artist"):
            continue
        rid = str(g["r"]) if g.get("r") else None
        key = rid or f"{_norm(g['a'])}|{_norm(g['t'])}"
        plays[str(g["u"])][key] += r["n"]
        catalog.setdefault(key, engine.Track(key, r["title"], r["artist"], rid))
    return plays, catalog


def _members_for(creator, user_ids, circle_id) -> tuple[list[User], object]:
    circle = None
    if circle_id:
        from circles.models import Circle

        if not CircleMember.objects.filter(circle_id=circle_id, user=creator).exists():
            raise ApiError("NOT_FOUND", "We couldn't find that circle.", 404)
        circle = Circle.objects.get(pk=circle_id)
        ids = set(CircleMember.objects.filter(circle=circle).values_list("user_id", flat=True))
    else:
        ids = set()
        for uid in user_ids:
            if not policy.are_friends(creator, uid):
                raise ApiError("NOT_FOUND", "You can make a Blend with friends or a circle.", 404)
            ids.add(uid)
        ids.add(creator.pk)
        if not engine.MIN_MEMBERS <= len(ids) <= engine.MAX_MEMBERS:
            raise ApiError("VALIDATION_ERROR", "Pick 1 to 5 friends for a Blend.", 400)
    users = [
        u
        for u in User.objects.filter(pk__in=ids, is_active=True, deleted_at__isnull=True)
        if u.pk == creator.pk or not policy.is_blocked_either_way(creator, u)
    ]
    if len(users) < engine.MIN_MEMBERS:
        raise ApiError("VALIDATION_ERROR", "A Blend needs at least two people.", 400)
    return users, circle


def _name(u: User) -> str:
    return (u.display_name or u.username).split(" ")[0]


@transaction.atomic
def create(creator, user_ids=(), circle_id=None, name: str = "") -> Blend:
    users, circle = _members_for(creator, [str(u) for u in user_ids], circle_id)
    if not name:
        name = (
            f"{circle.name} Blend" if circle else " + ".join(sorted(_name(u) for u in users))[:80]
        )
    blend = Blend.objects.create(name=name[:80], created_by=creator, circle=circle)
    BlendMember.objects.bulk_create(BlendMember(blend=blend, user=u) for u in users)
    generate(blend)
    return blend


def members(blend: Blend) -> list[User]:
    return list(
        User.objects.filter(pk__in=blend.members.values("user_id")).order_by("display_name")
    )


def require_member(blend_id, user) -> Blend:
    b = Blend.objects.filter(pk=blend_id, members__user=user).first()
    if b is None:
        raise ApiError("NOT_FOUND", "We couldn't find that Blend.", 404)
    return b


@transaction.atomic
def generate(blend: Blend) -> list[BlendTrack]:
    """(Re)generate: pinned tracks stay (JNG-07-03); every track gets a reason (JNG-07-02)."""
    people = members(blend)
    allowed = contributors(people)
    plays, catalog = load_plays(sorted(allowed))
    em = [
        engine.Member(str(u.pk), _name(u), plays.get(str(u.pk), Counter()))
        for u in people
        if str(u.pk) in allowed
    ]
    names = {str(u.pk): _name(u) for u in people}
    pins = [
        engine.Pick(
            engine.Track(
                str(t.recording_id or f"{_norm(t.artist)}|{_norm(t.title)}"),
                t.title,
                t.artist,
                str(t.recording_id) if t.recording_id else None,
            ),
            f"Pinned by {names.get(str(t.pinned_by_id), 'a member')}",
            t.contributor_ids,
            pinned=True,
        )
        for t in blend.tracks.filter(pinned_by__isnull=False)
        if str(t.pinned_by_id) in names
    ]
    pinned_by = {
        str(t.recording_id or f"{_norm(t.artist)}|{_norm(t.title)}"): t.pinned_by_id
        for t in blend.tracks.filter(pinned_by__isnull=False)
    }
    picks = [p for p in engine.generate(em, catalog, pins) if p.reason]
    blend.tracks.all().delete()
    rows = BlendTrack.objects.bulk_create(
        BlendTrack(
            blend=blend,
            position=i,
            recording_id=p.track.recording_id,
            title=p.track.title[:500],
            artist=p.track.artist[:500],
            reason=p.reason[:200],
            contributor_ids=p.contributor_ids,
            pinned_by_id=pinned_by.get(p.track.key) if p.pinned else None,
        )
        for i, p in enumerate(picks)
    )
    blend.generated_at = timezone.now()
    blend.save(update_fields=["generated_at"])
    return rows


def pin(track: BlendTrack, user, on: bool) -> BlendTrack:
    track.pinned_by = user if on else None
    track.save(update_fields=["pinned_by"])
    return track


@transaction.atomic
def leave(blend: Blend, user) -> None:
    BlendMember.objects.filter(blend=blend, user=user).delete()
    if blend.members.count() < engine.MIN_MEMBERS:
        blend.delete()
