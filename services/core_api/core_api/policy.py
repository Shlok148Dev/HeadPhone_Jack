"""Object-level visibility policy shared by every endpoint (BR-06, BR-07).

Friendships, blocks and circles are all live.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from typing import Any

from django.utils import timezone

# Request-scoped, bulk-loaded relationship data (load test 2026-10: the feed ran ~63 queries for
# 11 friends). Inside ``bulk(viewer, owners)`` checks between the viewer and anyone answer from
# memory; outside it, or for pairs not involving the viewer, every check still hits the database.
_bulk: ContextVar[dict[str, Any] | None] = ContextVar("policy_bulk", default=None)


@contextmanager
def bulk(viewer, owners: Iterable) -> Iterator[None]:
    from accounts.models import PrivacySettings
    from circles.models import CircleMember
    from social.services import blocked_ids, friend_ids

    owners = list(owners)
    vid = _id(viewer)
    mine = CircleMember.objects.filter(user_id=vid).values("circle_id")
    data: dict[str, Any] = {
        "viewer": vid,
        "blocked": {str(x) for x in blocked_ids(vid)},
        "friends": {str(x) for x in friend_ids(vid)},
        "mates": {
            str(x)
            for x in CircleMember.objects.filter(circle_id__in=mine).values_list(
                "user_id", flat=True
            )
        },
        "links": [],  # (recording_id, dict) filled in one query on exit
        "art": [],  # recording dicts enriched with artwork in one query on exit
    }
    rows = {
        str(p.user_id): p
        for p in PrivacySettings.objects.filter(user_id__in=[o.pk for o in owners])
    }
    for o in owners:
        p = rows.get(str(o.pk))
        if p is not None:
            p.user = o
            o._privacy_cache = p  # PrivacySettings.for_user reads this first
    token = _bulk.set(data)
    try:
        yield
        if data["art"]:
            from artwork.services import enrich

            enrich(data["art"])  # derived links (Apple) first …
        _fill_links(data["links"])  # … then verified links win
    finally:
        _bulk.reset(token)


def defer_links(recording_id, links: dict) -> bool:
    """Inside ``bulk``: register a card's link dict to be filled in one query. False outside."""
    data = _bulk.get()
    if data is None:
        return False
    data["links"].append((str(recording_id), links))
    return True


def defer_enrich(item: dict) -> bool:
    """Inside ``bulk``: queue a recording dict for one batched artwork lookup. False outside."""
    data = _bulk.get()
    if data is None:
        return False
    data["art"].append(item)
    return True


def _fill_links(pending: list) -> None:
    if not pending:
        return
    from sources.models import RecordingLink

    by: dict[str, dict] = {}
    for rid, platform, url in RecordingLink.objects.filter(
        recording_id__in={rid for rid, _ in pending}
    ).values_list("recording_id", "platform", "url"):
        by.setdefault(str(rid), {})[platform] = url
    for rid, links in pending:
        for platform, url in by.get(rid, {}).items():
            if platform in links:
                links[platform] = url  # verified links win over derived ones


def _other(a, b) -> str | None:
    data = _bulk.get()
    if data is None:
        return None
    if _id(a) == data["viewer"]:
        return _id(b)
    if _id(b) == data["viewer"]:
        return _id(a)
    return None


def _id(user) -> str:
    return str(getattr(user, "pk", user))


def is_blocked_either_way(a, b) -> bool:
    """BR-07: a block in either direction overrides every relationship."""
    other = _other(a, b)
    if other is not None:
        return other in _bulk.get()["blocked"]
    from social.services import blocked_either_way

    return blocked_either_way(_id(a), _id(b))


def are_friends(a, b) -> bool:
    """BR-06: true only for an accepted friendship."""
    other = _other(a, b)
    if other is not None:
        return other in _bulk.get()["friends"]
    from social.models import FriendshipStatus
    from social.services import pair

    f = pair(_id(a), _id(b))
    return f is not None and f.status == FriendshipStatus.ACCEPTED


def share_circle(a, b) -> bool:
    other = _other(a, b)
    if other is not None:
        return other in _bulk.get()["mates"]
    from circles.models import CircleMember

    mine = CircleMember.objects.filter(user_id=_id(a)).values("circle_id")
    return CircleMember.objects.filter(user_id=_id(b), circle_id__in=mine).exists()


def is_private_now(owner, now: datetime | None = None) -> bool:
    """JNG-02-06: Private mode hides all activity until ``private_until``."""
    until = getattr(owner, "private_until", None)
    return bool(until and until > (now or timezone.now()))


def can_view_activity(viewer, owner, now: datetime | None = None) -> bool:
    """Whether ``viewer`` may see ``owner``'s listening activity.

    The owner always sees their own card. Everyone else is subject to blocks (BR-07), Private mode
    (JNG-02-06), ``activity_visibility`` (JNG-02-05) and friendship/circle membership (BR-06).
    """
    if viewer is None or owner is None:
        return False
    if _id(viewer) == _id(owner):
        return True
    if getattr(owner, "deleted_at", None) is not None:
        return False
    if is_blocked_either_way(viewer, owner):
        return False
    if is_private_now(owner, now):
        return False
    from accounts.models import ActivityVisibility, PrivacySettings

    privacy = PrivacySettings.for_user(owner)
    if privacy.activity_visibility == ActivityVisibility.NOBODY:
        return False
    if privacy.activity_visibility == ActivityVisibility.CIRCLES:
        # "Only circles I choose": friendship alone isn't enough (JNG-02-05, UX_SPEC 5.3).
        return share_circle(viewer, owner)
    return are_friends(viewer, owner)
