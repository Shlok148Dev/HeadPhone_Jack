"""Object-level visibility policy shared by every endpoint (BR-06, BR-07).

Friendships, blocks and circles are all live.
"""

from __future__ import annotations

from datetime import datetime

from django.utils import timezone


def _id(user) -> str:
    return str(getattr(user, "pk", user))


def is_blocked_either_way(a, b) -> bool:
    """BR-07: a block in either direction overrides every relationship."""
    from social.services import blocked_either_way

    return blocked_either_way(_id(a), _id(b))


def are_friends(a, b) -> bool:
    """BR-06: true only for an accepted friendship."""
    from social.models import FriendshipStatus
    from social.services import pair

    f = pair(_id(a), _id(b))
    return f is not None and f.status == FriendshipStatus.ACCEPTED


def share_circle(a, b) -> bool:
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
