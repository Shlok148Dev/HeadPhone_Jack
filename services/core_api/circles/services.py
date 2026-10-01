"""Circle rules (EP-04). Every change goes through here so limits and roles hold everywhere."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from core_api import events, policy
from core_api.errors import ApiError

from .models import (
    INVITE_DAYS,
    MAX_CIRCLES_PER_USER,
    MAX_MEMBERS,
    Circle,
    CircleInvite,
    CircleMember,
    Role,
)

FULL = ApiError("CIRCLE_FULL", "This circle is full", 409)


def membership(circle: Circle, user) -> CircleMember | None:
    return CircleMember.objects.filter(circle=circle, user=user).first()


def require_member(circle: Circle, user) -> CircleMember:
    m = membership(circle, user)
    if m is None:
        raise ApiError("NOT_FOUND", "We couldn't find that circle.", 404)  # never confirm existence
    return m


def require_admin(circle: Circle, user) -> CircleMember:
    m = require_member(circle, user)
    if m.role not in (Role.OWNER, Role.ADMIN):
        raise ApiError("FORBIDDEN", "Only the circle's admins can do that.", 403)
    return m


def _check_room(user) -> None:
    if CircleMember.objects.filter(user=user).count() >= MAX_CIRCLES_PER_USER:
        raise ApiError("CIRCLE_LIMIT", f"You can be in up to {MAX_CIRCLES_PER_USER} circles.", 409)


def _changed(circle: Circle, user_ids) -> None:
    events.publish_domain(
        "friendship.changed", {"user_ids": [str(u) for u in user_ids], "change": "circle"}
    )


@transaction.atomic
def create_circle(owner, name: str, visibility: str = "private") -> Circle:
    _check_room(owner)
    c = Circle.objects.create(
        name=name.strip()[:60], owner=owner, visibility=visibility, member_count=1
    )
    CircleMember.objects.create(circle=c, user=owner, role=Role.OWNER)
    return c


@transaction.atomic
def _join(circle: Circle, user) -> CircleMember:
    """Add one member who accepted (BR-08). Row lock keeps the 50 limit under concurrency."""
    c = Circle.objects.select_for_update().get(pk=circle.pk)
    existing = membership(c, user)
    if existing:
        return existing
    if c.member_count >= MAX_MEMBERS:
        raise FULL
    _check_room(user)
    if any(
        policy.is_blocked_either_way(user, m.user_id) for m in c.members.filter(role=Role.OWNER)
    ):
        raise ApiError("NOT_FOUND", "This invite doesn't work any more.", 404)
    try:
        m = CircleMember.objects.create(circle=c, user=user, role=Role.MEMBER)
    except IntegrityError:
        return membership(c, user)  # type: ignore[return-value]
    Circle.objects.filter(pk=c.pk).update(member_count=F("member_count") + 1)
    _changed(c, [user.pk])
    return m


def _can_invite(circle: Circle, m: CircleMember) -> None:
    if m.role == Role.MEMBER and not circle.members_can_invite:
        raise ApiError("FORBIDDEN", "Only admins can invite people to this circle.", 403)


def invite_friend(circle: Circle, inviter, invitee) -> CircleInvite:
    """JNG-04-02: invite a friend; they join only by accepting (BR-08)."""
    _can_invite(circle, require_member(circle, inviter))
    if not policy.are_friends(inviter, invitee):
        raise ApiError("NOT_FOUND", "You can only invite your friends.", 404)
    if membership(circle, invitee):
        raise ApiError("ALREADY_MEMBER", "They're already in this circle.", 409)
    if circle.member_count >= MAX_MEMBERS:
        raise FULL
    inv, _ = CircleInvite.objects.get_or_create(
        circle=circle,
        invitee=invitee,
        revoked=False,
        uses=0,
        defaults={
            "created_by": inviter,
            "expires_at": timezone.now() + timedelta(days=INVITE_DAYS),
        },
    )
    from notifications.services import notify

    notify(
        invitee.pk,
        "circle_invite",
        f"{inviter.display_name or inviter.username} invited you to {circle.name}",
        url="/circles",
    )
    return inv


def accept_invite(inv: CircleInvite, user) -> CircleMember:
    if inv.invitee_id != user.pk or inv.revoked or inv.uses or inv.expires_at < timezone.now():
        raise ApiError("NOT_FOUND", "This invite doesn't work any more.", 404)
    m = _join(inv.circle, user)
    CircleInvite.objects.filter(pk=inv.pk).update(uses=1)
    return m


def decline_invite(inv: CircleInvite, user) -> None:
    if inv.invitee_id != user.pk:
        raise ApiError("NOT_FOUND", "This invite doesn't work any more.", 404)
    inv.delete()


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_link(circle: Circle, user) -> tuple[str, CircleInvite]:
    """JNG-04-02: a share link that expires in 7 days. Only the hash is stored."""
    _can_invite(circle, require_member(circle, user))
    token = secrets.token_urlsafe(16)
    inv = CircleInvite.objects.create(
        circle=circle,
        created_by=user,
        token_hash=_hash(token),
        expires_at=timezone.now() + timedelta(days=INVITE_DAYS),
    )
    return token, inv


def link_invite(token: str) -> CircleInvite:
    inv = CircleInvite.objects.select_related("circle").filter(token_hash=_hash(token[:64])).first()
    if inv is None or inv.revoked or inv.expires_at < timezone.now() or inv.uses >= inv.max_uses:
        raise ApiError("NOT_FOUND", "This invite link doesn't work any more.", 404)
    return inv


def join_by_link(token: str, user) -> CircleMember:
    inv = link_invite(token)
    if inv.circle.member_count >= MAX_MEMBERS and not membership(inv.circle, user):
        raise FULL  # SRS Gherkin "Full circle"
    m = _join(inv.circle, user)
    CircleInvite.objects.filter(pk=inv.pk).update(uses=F("uses") + 1)
    return m


def set_role(circle: Circle, actor, target_id, role: str) -> CircleMember:
    """JNG-04-03: only the owner makes or unmakes admins."""
    if require_member(circle, actor).role != Role.OWNER:
        raise ApiError("FORBIDDEN", "Only the owner can change roles.", 403)
    if role not in (Role.ADMIN, Role.MEMBER):
        raise ApiError("VALIDATION_ERROR", "Choose admin or member.", 400)
    m = CircleMember.objects.filter(circle=circle, user_id=target_id).first()
    if m is None or m.role == Role.OWNER:
        raise ApiError("NOT_FOUND", "That person isn't a member.", 404)
    m.role = role
    m.save(update_fields=["role"])
    return m


@transaction.atomic
def remove_member(circle: Circle, actor, target_id) -> None:
    """JNG-04-06: admins remove members; only the owner removes admins; nobody removes the owner."""
    actor_m = require_admin(circle, actor)
    m = CircleMember.objects.filter(circle=circle, user_id=target_id).first()
    if m is None or m.role == Role.OWNER:
        raise ApiError("NOT_FOUND", "That person isn't a member.", 404)
    if m.role == Role.ADMIN and actor_m.role != Role.OWNER:
        raise ApiError("FORBIDDEN", "Only the owner can remove an admin.", 403)
    m.delete()
    Circle.objects.filter(pk=circle.pk).update(member_count=F("member_count") - 1)
    _changed(circle, [target_id])


@transaction.atomic
def leave(circle: Circle, user) -> None:
    m = require_member(circle, user)
    if m.role == Role.OWNER:
        if circle.member_count > 1:
            raise ApiError(
                "OWNER_MUST_TRANSFER", "Hand the circle to someone else before you leave.", 409
            )
        circle.delete()  # last person out closes the circle
        return
    m.delete()
    Circle.objects.filter(pk=circle.pk).update(member_count=F("member_count") - 1)
    _changed(circle, [user.pk])


@transaction.atomic
def transfer(circle: Circle, owner, new_owner_id) -> None:
    if require_member(circle, owner).role != Role.OWNER:
        raise ApiError("FORBIDDEN", "Only the owner can hand over the circle.", 403)
    target = CircleMember.objects.filter(circle=circle, user_id=new_owner_id).first()
    if target is None or target.user_id == owner.pk:
        raise ApiError("NOT_FOUND", "Choose another member.", 404)
    CircleMember.objects.filter(circle=circle, user=owner).update(role=Role.ADMIN)
    target.role = Role.OWNER
    target.save(update_fields=["role"])
    Circle.objects.filter(pk=circle.pk).update(owner_id=new_owner_id)


def co_member_ids(user_id) -> set:
    circles = CircleMember.objects.filter(user_id=user_id).values("circle_id")
    return set(
        CircleMember.objects.filter(circle_id__in=circles)
        .exclude(user_id=user_id)
        .values_list("user_id", flat=True)
    )
