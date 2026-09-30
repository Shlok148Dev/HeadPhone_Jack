"""Social graph (Tech Bible 3.1): friendships, blocks, reports, invite links (EP-02, JNG-12-01)."""

import secrets
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class FriendshipStatus(models.TextChoices):
    PENDING = "pending"
    ACCEPTED = "accepted"


class Friendship(TimeStamped):
    """One row per pair; ``user_low < user_high`` (by UUID string) so a pair can't be duplicated."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_low = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    user_high = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    status = models.CharField(
        max_length=10, choices=FriendshipStatus.choices, default=FriendshipStatus.PENDING
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "friendships"
        constraints = [
            models.UniqueConstraint(fields=["user_low", "user_high"], name="friendships_pair"),
            models.CheckConstraint(
                condition=~Q(user_low=models.F("user_high")), name="friendships_not_self"
            ),
        ]
        indexes = [
            models.Index(
                fields=["user_low"], condition=Q(status="accepted"), name="friendships_accepted_low"
            ),
            models.Index(
                fields=["user_high"],
                condition=Q(status="accepted"),
                name="friendships_accepted_high",
            ),
        ]

    def __str__(self) -> str:
        return f"friendship {self.pk} ({self.status})"

    @staticmethod
    def ordered(a_id, b_id):
        return (a_id, b_id) if str(a_id) < str(b_id) else (b_id, a_id)

    def other(self, user_id):
        return self.user_high_id if str(self.user_low_id) == str(user_id) else self.user_low_id


class Block(TimeStamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_made"
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )

    class Meta:
        db_table = "blocks"
        constraints = [models.UniqueConstraint(fields=["blocker", "blocked"], name="blocks_pair")]

    def __str__(self) -> str:
        return f"block {self.pk}"


class ReportReason(models.TextChoices):
    SPAM = "spam"
    HARASSMENT = "harassment"
    HATE = "hate"
    IMPERSONATION = "impersonation"
    INAPPROPRIATE = "inappropriate"
    OTHER = "other"


class Report(TimeStamped):
    """JNG-12-01. Reviewed in the moderation console (Sprint 10)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    target_type = models.CharField(max_length=20, default="user")
    target_id = models.UUIDField()
    reason = models.CharField(max_length=20, choices=ReportReason.choices)
    details = models.TextField(blank=True, max_length=1000)
    status = models.CharField(max_length=20, default="open")

    class Meta:
        db_table = "reports"

    def __str__(self) -> str:
        return f"report {self.pk} ({self.reason})"


def _code() -> str:
    return secrets.token_urlsafe(9)


class InviteLink(TimeStamped):
    """A personal, revocable link that auto-sends a friend request to its owner (JNG-02-07)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invite_link"
    )
    code = models.CharField(max_length=24, unique=True, default=_code)

    class Meta:
        db_table = "invite_links"

    def __str__(self) -> str:
        return f"invite {self.code}"
