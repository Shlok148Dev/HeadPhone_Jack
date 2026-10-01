"""Moderation and admin audit (EP-12; ADR-0023)."""

import uuid

from django.conf import settings
from django.db import models


class ActionKind(models.TextChoices):
    WARN = "warn"
    MUTE = "mute"  # can't post songs, notes, nominations or names
    SUSPEND = "suspend"  # can't use the app until it ends
    BAN = "ban"  # account deactivated


class ModerationAction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="moderation_actions"
    )
    kind = models.CharField(max_length=10, choices=ActionKind.choices)
    reason = models.CharField(max_length=500)
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    report = models.ForeignKey(
        "social.Report", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    lifted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "moderation_actions"
        indexes = [models.Index(fields=["user", "-created_at"], name="modactions_user")]

    def __str__(self) -> str:
        return f"{self.kind} {self.user_id}"


class Appeal(models.Model):
    """JNG-12-08: one appeal per action, decided by a different moderator where possible."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.OneToOneField(ModerationAction, on_delete=models.CASCADE, related_name="appeal")
    text = models.CharField(max_length=1000)
    status = models.CharField(max_length=10, default="open")  # open | upheld | overturned
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decision_note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "moderation_appeals"

    def __str__(self) -> str:
        return f"appeal {self.action_id} {self.status}"


class AuditEntry(models.Model):
    """JNG-12-03: append-only record of every staff action (moderation, flags, allowlist)."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    action = models.CharField(max_length=40)
    target = models.CharField(max_length=80)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} {self.target}"


class AllowlistEntry(models.Model):
    """JNG-12-06: Spotify direct-route testers (Spotify development mode allows 5)."""

    email = models.EmailField(unique=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spotify_allowlist"

    def __str__(self) -> str:
        return self.email
