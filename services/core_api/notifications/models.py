"""Notifications (EP-11; ADR-0023): in-app centre, per-type controls, quiet hours, web push."""

import uuid

from django.conf import settings
from django.db import models

TYPES = (
    "friend_request",
    "circle_invite",
    "send",
    "session_invite",
    "battle",
    "recap",
    "moderation",
)
LABELS = {
    "friend_request": "Friend requests",
    "circle_invite": "Circle invites",
    "send": "Songs sent to you",
    "session_invite": "Listening sessions",
    "battle": "Battles",
    "recap": "Monthly recap",
    "moderation": "Account and safety",
}
PUSH_CAP_DEFAULT = 5  # JNG-11-07
PUSH_CAP_MAX = 20


def default_types() -> dict:
    return {t: {"in_app": True, "push": True} for t in TYPES}


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(max_length=24)
    title = models.CharField(max_length=200)
    url = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    pushed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications"
        indexes = [models.Index(fields=["user", "-created_at"], name="notifications_user")]

    def __str__(self) -> str:
        return f"{self.type} to {self.user_id}"


class NotificationPrefs(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_prefs"
    )
    types = models.JSONField(default=default_types)
    quiet_start = models.CharField(max_length=5, default="23:00")  # JNG-11-04
    quiet_end = models.CharField(max_length=5, default="08:00")
    tz = models.CharField(max_length=64, default="Asia/Kolkata")
    push_daily_cap = models.PositiveSmallIntegerField(default=PUSH_CAP_DEFAULT)

    class Meta:
        db_table = "notification_prefs"

    def __str__(self) -> str:
        return f"prefs {self.user_id}"

    @classmethod
    def for_user(cls, user_id) -> "NotificationPrefs":
        p, _ = cls.objects.get_or_create(user_id=user_id)
        return p

    def allows(self, type_: str, channel: str) -> bool:
        return bool({**default_types(), **(self.types or {})}.get(type_, {}).get(channel, True))


class PushSubscription(models.Model):
    """A browser's push endpoint. Exists only after the person allowed push (JNG-11-02)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    endpoint = models.URLField(max_length=800, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "push_subscriptions"

    def __str__(self) -> str:
        return f"push {self.user_id}"
