"""Object-level visibility policy shared by every endpoint (BR-06, BR-07).

Friendships, blocks and circles arrive in Sprint 3; until then only the owner can see their own
activity. Querysets and views must call these helpers rather than re-implementing the rules.
"""

from __future__ import annotations

from datetime import datetime

from django.utils import timezone


def _id(user) -> str:
    return str(getattr(user, "pk", user))


def is_blocked_either_way(a, b) -> bool:
    """BR-07: a block in either direction overrides every relationship."""
    # TODO(S3): query the blocks table (blocker_id, blocked_id) in both directions.
    return False


def are_friends(a, b) -> bool:
    """BR-06: true only for an accepted friendship."""
    # TODO(S3): query friendships (user_low_id, user_high_id, status='accepted').
    return False


def share_circle(a, b) -> bool:
    # TODO(S6): query circle_members for a shared circle.
    return False


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
    if are_friends(viewer, owner):
        return True
    if privacy.activity_visibility == ActivityVisibility.CIRCLES:
        return share_circle(viewer, owner)
    return False
