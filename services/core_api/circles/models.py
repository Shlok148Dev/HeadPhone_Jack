"""Circles (Tech Bible 3.1, 5.5; EP-04). Nobody joins without accepting (BR-08)."""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

MAX_MEMBERS = 50  # JNG-04-01
MAX_CIRCLES_PER_USER = 20  # JNG-04-08
INVITE_DAYS = 7  # JNG-04-02


def default_battle_schedule() -> dict:
    # Tech Bible 7.4 (IST): nominations Mon 18:00 → Fri 18:00, voting → Sun 21:00.
    return {"nominate": "MON 18:00", "vote": "FRI 18:00", "close": "SUN 21:00", "skip_week": None}


class Visibility(models.TextChoices):
    PRIVATE = "private"
    DISCOVERABLE = "discoverable"


class Role(models.TextChoices):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Circle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=60)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    visibility = models.CharField(
        max_length=16, choices=Visibility.choices, default=Visibility.PRIVATE
    )
    member_count = models.PositiveSmallIntegerField(default=0)
    members_can_invite = models.BooleanField(default=True)
    battle_schedule = models.JSONField(default=default_battle_schedule)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "circles"
        constraints = [
            models.CheckConstraint(
                condition=Q(member_count__lte=MAX_MEMBERS), name="circle_max_members"
            )
        ]

    def __str__(self) -> str:
        return self.name


class CircleMember(models.Model):
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="circle_memberships"
    )
    role = models.CharField(max_length=8, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "circle_members"
        constraints = [
            models.UniqueConstraint(fields=["circle", "user"], name="circle_member_unique")
        ]

    def __str__(self) -> str:
        return f"{self.user_id} in {self.circle_id}"


class CircleInvite(models.Model):
    """A direct invite to one friend (``invitee`` set) or a shareable link (``token_hash`` set)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name="invites")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    invitee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="circle_invites",
    )
    token_hash = models.CharField(max_length=64, blank=True, db_index=True)
    expires_at = models.DateTimeField()
    max_uses = models.PositiveSmallIntegerField(default=MAX_MEMBERS)
    uses = models.PositiveSmallIntegerField(default=0)
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "circle_invites"

    def __str__(self) -> str:
        return f"invite {self.pk}"


class SuggestedCircle(models.Model):
    """Leiden community suggested to one member (Tech Bible 5.5); never auto-joins anyone."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    for_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    member_ids = models.JSONField(default=list)
    name = models.CharField(max_length=60)
    status = models.CharField(max_length=12, default="pending")  # pending | used | dismissed
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "suggested_circles"

    def __str__(self) -> str:
        return self.name
