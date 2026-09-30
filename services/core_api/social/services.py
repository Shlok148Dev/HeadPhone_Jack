"""Social-graph rules (EP-02). Views stay thin; every rule lives here and in core_api.policy."""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from core_api import events
from core_api.errors import ApiError

from .models import Block, Friendship, FriendshipStatus, InviteLink

DAILY_REQUEST_LIMIT = 30  # NFR-SEC-04


def pair(a_id, b_id) -> Friendship | None:
    low, high = Friendship.ordered(a_id, b_id)
    return Friendship.objects.filter(user_low_id=low, user_high_id=high).first()


def blocked_either_way(a_id, b_id) -> bool:
    return Block.objects.filter(
        Q(blocker_id=a_id, blocked_id=b_id) | Q(blocker_id=b_id, blocked_id=a_id)
    ).exists()


def blocked_ids(user_id) -> set:
    """Everyone this user blocked or was blocked by (BR-07 filter for lists and search)."""
    rows = Block.objects.filter(Q(blocker_id=user_id) | Q(blocked_id=user_id)).values_list(
        "blocker_id", "blocked_id"
    )
    return {b if str(a) == str(user_id) else a for a, b in rows}


def friend_ids(user_id) -> list:
    rows = Friendship.objects.filter(
        Q(user_low_id=user_id) | Q(user_high_id=user_id), status=FriendshipStatus.ACCEPTED
    ).values_list("user_low_id", "user_high_id")
    return [h if str(lo) == str(user_id) else lo for lo, h in rows]


def _changed(a_id, b_id, kind: str) -> None:
    events.publish_domain(
        "friendship.changed", {"user_ids": [str(a_id), str(b_id)], "change": kind}
    )


def send_request(sender, target) -> Friendship:
    """JNG-02-02. A request to someone who already asked you accepts both at once."""
    if str(sender.pk) == str(target.pk):
        raise ApiError("INVALID_TARGET", "You can't add yourself.", 400)
    if (
        not target.is_active
        or target.deleted_at is not None
        or blocked_either_way(sender.pk, target.pk)
    ):
        # Same answer as "no such user": never reveal a block (JNG-02-04).
        raise ApiError("NOT_FOUND", "We couldn't find that person.", 404)
    existing = pair(sender.pk, target.pk)
    if existing:
        if existing.status == FriendshipStatus.ACCEPTED:
            return existing
        if str(existing.requested_by_id) != str(sender.pk):  # duplicate request → one friendship
            return accept(sender, existing)
        return existing
    since = timezone.now() - timezone.timedelta(days=1)
    sent_today = Friendship.objects.filter(requested_by=sender, created_at__gte=since).count()
    if sent_today >= DAILY_REQUEST_LIMIT:
        raise ApiError(
            "RATE_LIMITED", "You've sent a lot of requests today. Try again tomorrow.", 429
        )
    low, high = Friendship.ordered(sender.pk, target.pk)
    try:
        with transaction.atomic():
            f = Friendship.objects.create(user_low_id=low, user_high_id=high, requested_by=sender)
    except IntegrityError:  # a concurrent request created the pair
        f = pair(sender.pk, target.pk)
        assert f is not None
        if f.status == FriendshipStatus.PENDING and str(f.requested_by_id) != str(sender.pk):
            return accept(sender, f)
        return f
    events.publish_domain(
        "notify", {"user_id": str(target.pk), "type": "friend_request", "id": str(f.pk)}
    )
    return f


def _for_recipient(user, f: Friendship) -> None:
    if (
        f.status != FriendshipStatus.PENDING
        or str(f.requested_by_id) == str(user.pk)
        or str(user.pk) not in (str(f.user_low_id), str(f.user_high_id))
    ):
        raise ApiError("NOT_FOUND", "That request isn't there any more.", 404)


def accept(user, f: Friendship) -> Friendship:
    _for_recipient(user, f)
    f.status, f.accepted_at = FriendshipStatus.ACCEPTED, timezone.now()
    f.save(update_fields=["status", "accepted_at", "updated_at"])
    _changed(f.user_low_id, f.user_high_id, "accepted")
    from jingle_ml.tasks import schedule_recompute

    transaction.on_commit(lambda: schedule_recompute(f.user_low_id, f.user_high_id))
    return f


def decline(user, f: Friendship) -> None:
    _for_recipient(user, f)
    f.delete()  # the sender is not told (JNG-02-02)


def cancel(user, f: Friendship) -> None:
    if f.status != FriendshipStatus.PENDING or str(f.requested_by_id) != str(user.pk):
        raise ApiError("NOT_FOUND", "That request isn't there any more.", 404)
    f.delete()


def remove_friend(user, other_id) -> None:
    """JNG-02-03: they stop seeing your activity at once (policy reads the table every time)."""
    f = pair(user.pk, other_id)
    if f is None or f.status != FriendshipStatus.ACCEPTED:
        raise ApiError("NOT_FOUND", "You aren't friends with that person.", 404)
    f.delete()
    _changed(user.pk, other_id, "removed")


def block(user, other) -> None:
    """JNG-02-04, BR-07: hides both people from each other everywhere; no notification."""
    if str(user.pk) == str(other.pk):
        raise ApiError("INVALID_TARGET", "You can't block yourself.", 400)
    with transaction.atomic():
        Block.objects.get_or_create(blocker=user, blocked=other)
        f = pair(user.pk, other.pk)
        if f:
            f.delete()
    events.publish_domain("block.created", {"user_ids": [str(user.pk), str(other.pk)]})


def unblock(user, other_id) -> None:
    Block.objects.filter(blocker=user, blocked_id=other_id).delete()


def invite_for(user) -> InviteLink:
    link, _ = InviteLink.objects.get_or_create(owner=user)
    return link


def rotate_invite(user) -> InviteLink:
    InviteLink.objects.filter(owner=user).delete()
    return InviteLink.objects.create(owner=user)


def relationship(viewer_id, other_id) -> str:
    """UI button state: self | friends | outgoing | incoming | none (blocked users never listed)."""
    if str(viewer_id) == str(other_id):
        return "self"
    f = pair(viewer_id, other_id)
    if f is None:
        return "none"
    if f.status == FriendshipStatus.ACCEPTED:
        return "friends"
    return "outgoing" if str(f.requested_by_id) == str(viewer_id) else "incoming"
