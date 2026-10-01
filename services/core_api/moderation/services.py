"""Moderation rules (JNG-12-02, 03, 08) and their effects on the rest of the app."""

from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core_api.errors import ApiError

from .models import ActionKind, AllowlistEntry, Appeal, AuditEntry, ModerationAction

SPOTIFY_ALLOWLIST_MAX = 5


def audit(actor, action: str, target: str, **details) -> AuditEntry:
    return AuditEntry.objects.create(
        actor=actor, action=action, target=target[:80], details=details
    )


def active(user, kind: str):
    now = timezone.now()
    return (
        ModerationAction.objects.filter(user=user, kind=kind, lifted_at__isnull=True)
        .exclude(expires_at__lt=now)
        .order_by("-expires_at")
        .first()
    )


def _until(a: ModerationAction) -> str:
    if a.expires_at is None:
        return ""
    return " until " + timezone.localtime(a.expires_at).strftime("%d %b, %H:%M")


def require_not_muted(user) -> None:
    """Mutes stop new public content: sends, notes, nominations, queue adds, names."""
    a = active(user, ActionKind.MUTE)
    if a is not None:
        raise ApiError(
            "MUTED", f"Your account is muted{_until(a)}. You can appeal in Settings.", 403
        )


def require_not_suspended(user) -> None:
    a = active(user, ActionKind.SUSPEND)
    if a is not None:
        raise ApiError(
            "SUSPENDED", f"Your account is suspended{_until(a)}. You can appeal in Settings.", 403
        )


@transaction.atomic
def act(
    moderator, user, kind: str, reason: str, days: int | None = None, report=None
) -> ModerationAction:
    if kind not in ActionKind.values:
        raise ApiError("VALIDATION_ERROR", "Choose warn, mute, suspend or ban.", 400)
    if user.pk == moderator.pk:
        raise ApiError("FORBIDDEN", "You can't moderate your own account.", 403)
    reason = (reason or "").strip()
    if not reason:
        raise ApiError("VALIDATION_ERROR", "Give a reason. The person sees it.", 400)
    expires = (
        timezone.now() + timedelta(days=days)
        if days and kind in (ActionKind.MUTE, ActionKind.SUSPEND)
        else None
    )
    a = ModerationAction.objects.create(
        user=user,
        kind=kind,
        reason=reason[:500],
        moderator=moderator,
        report=report,
        expires_at=expires,
    )
    if kind == ActionKind.BAN:
        user.is_active = False
        user.save(update_fields=["is_active"])
    if report is not None:
        report.status = "actioned"
        report.save(update_fields=["status"])
    audit(
        moderator,
        f"moderation.{kind}",
        f"user:{user.pk}",
        reason=reason[:200],
        days=days,
        report=str(report.pk) if report else None,
    )
    from notifications.services import notify

    if kind != ActionKind.BAN:
        words = {"warn": "a warning", "mute": "a mute", "suspend": "a suspension"}[kind]
        notify(
            user.pk,
            "moderation",
            f"Your account received {words}: {reason[:120]}",
            url="/settings/account",
        )
    return a


def dismiss(moderator, report) -> None:
    report.status = "dismissed"
    report.save(update_fields=["status"])
    audit(moderator, "report.dismiss", f"report:{report.pk}")


def appeal(user, action: ModerationAction, text: str) -> Appeal:
    if action.user_id != user.pk:
        raise ApiError("NOT_FOUND", "We couldn't find that action.", 404)
    text = (text or "").strip()
    if not text:
        raise ApiError("VALIDATION_ERROR", "Tell us why this should be reviewed.", 400)
    if hasattr(action, "appeal"):
        raise ApiError("ALREADY_APPEALED", "You've already appealed this.", 409)
    return Appeal.objects.create(action=action, text=text[:1000])


@transaction.atomic
def decide(moderator, ap: Appeal, overturn: bool, note: str = "") -> Appeal:
    if ap.status != "open":
        raise ApiError("ALREADY_DECIDED", "This appeal has been decided.", 409)
    ap.status = "overturned" if overturn else "upheld"
    ap.decided_by, ap.decided_at, ap.decision_note = moderator, timezone.now(), (note or "")[:500]
    ap.save()
    if overturn:
        a = ap.action
        a.lifted_at = timezone.now()
        a.save(update_fields=["lifted_at"])
        if a.kind == ActionKind.BAN:
            a.user.is_active = True
            a.user.save(update_fields=["is_active"])
    audit(
        moderator, f"appeal.{ap.status}", f"user:{ap.action.user_id}", action_id=str(ap.action_id)
    )
    from notifications.services import notify

    notify(
        ap.action.user_id,
        "moderation",
        "Your appeal was accepted"
        if overturn
        else "Your appeal was reviewed and the decision stands",
        url="/settings/account",
    )
    return ap


def allowlist_emails() -> set[str]:
    return set(AllowlistEntry.objects.values_list("email", flat=True))


def allowlist_add(actor, email: str) -> AllowlistEntry:
    email = (email or "").strip().lower()
    if "@" not in email:
        raise ApiError("VALIDATION_ERROR", "Enter an email address.", 400)
    if (
        AllowlistEntry.objects.count() >= SPOTIFY_ALLOWLIST_MAX
        and not AllowlistEntry.objects.filter(email=email).exists()
    ):
        raise ApiError(
            "ALLOWLIST_FULL",
            f"Spotify allows {SPOTIFY_ALLOWLIST_MAX} testers in development mode. "
            "Remove one first.",
            409,
        )
    e, _ = AllowlistEntry.objects.get_or_create(email=email, defaults={"added_by": actor})
    audit(actor, "allowlist.add", f"email:{email}")
    return e


def allowlist_remove(actor, email: str) -> None:
    AllowlistEntry.objects.filter(email=(email or "").strip().lower()).delete()
    audit(actor, "allowlist.remove", f"email:{email}")
