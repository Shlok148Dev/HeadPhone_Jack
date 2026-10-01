"""What a moderator sees for a report (JNG-12-02), and what members may report (JNG-12-01)."""

from __future__ import annotations

import uuid

from accounts.models import User
from core_api.errors import ApiError


def _uuid(value) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise ApiError("NOT_FOUND", "We couldn't find that.", 404) from None


def reportable(kind: str, target_id, reporter) -> uuid.UUID:
    """Members can report only things they can see: circles they're in, notes sent to them."""
    from circles.models import CircleMember
    from sends.models import Delivery

    tid = _uuid(target_id)
    if kind == "circle" and CircleMember.objects.filter(circle_id=tid, user=reporter).exists():
        return tid
    if kind == "send" and Delivery.objects.filter(pk=tid, recipient=reporter).exists():
        return tid
    raise ApiError("NOT_FOUND", "We couldn't find that.", 404)


def _person(u: User | None) -> dict | None:
    if u is None:
        return None
    return {"id": str(u.pk), "username": u.username, "display_name": u.display_name or u.username}


def describe(report) -> dict:
    """The reported content and the account responsible for it."""
    from circles.models import Circle
    from sends.models import Delivery

    content, owner = "", None
    if report.target_type == "user":
        owner = User.objects.filter(pk=report.target_id).first()
        content = (
            f"Profile: {owner.display_name} (@{owner.username})" if owner else "Deleted account"
        )
    elif report.target_type == "circle":
        c = Circle.objects.select_related("owner").filter(pk=report.target_id).first()
        owner = c.owner if c else None
        content = f"Circle name: {c.name}" if c else "Deleted circle"
    elif report.target_type == "send":
        d = Delivery.objects.select_related("rec__sender").filter(pk=report.target_id).first()
        owner = d.rec.sender if d else None
        content = f"Note: “{d.rec.note}”" if d and d.rec.note else "Song sent without a note"
    from social.models import Report

    prior = Report.objects.filter(target_id=report.target_id).exclude(pk=report.pk).count()
    from .models import ModerationAction

    return {
        "content": content,
        "responsible": _person(owner),
        "other_reports": prior,
        "past_actions": ModerationAction.objects.filter(user=owner).count() if owner else 0,
    }
