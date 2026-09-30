"""Live listening sessions (Technical Bible 3.1, 4.3; EP-07: JNG-07-05…09; ADR-0021).

Everyone plays on their own app; the room shares a queue the group steers with votes.
PostgreSQL is the source of truth; Redis ``sess:{id}:ver`` orders every change for clients.
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

MAX_PARTICIPANTS = 50
MAX_QUEUE = 100


class ListeningSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=80)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    circle = models.ForeignKey(
        "circles.Circle", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    now_playing = models.ForeignKey(
        "QueueEntry", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "sessions"

    def __str__(self) -> str:
        return self.title


class Participant(models.Model):
    session = models.ForeignKey(
        ListeningSession, on_delete=models.CASCADE, related_name="participants"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    invited = models.BooleanField(default=False)
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "session_participants"
        constraints = [
            models.UniqueConstraint(fields=["session", "user"], name="session_participant_once")
        ]

    def __str__(self) -> str:
        return f"{self.user_id} in {self.session_id}"


class QueueEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ListeningSession, on_delete=models.CASCADE, related_name="queue")
    recording = models.ForeignKey(
        "sources.Recording", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    title = models.CharField(max_length=500)
    artist = models.CharField(max_length=500)
    # Shown to the room; null when added anonymously (JNG-07-06).
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Never exposed: limits and moderation only (ADR-0021).
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    idempotency_key = models.CharField(max_length=64)
    score = models.IntegerField(default=0)
    played_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "session_queue"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "idempotency_key"], name="session_queue_idempotent"
            )
        ]
        indexes = [
            models.Index(
                fields=["session", "-score", "created_at"],
                condition=Q(played_at__isnull=True),
                name="session_queue_order",
            )
        ]

    def __str__(self) -> str:
        return f"{self.artist} - {self.title}"


class Vote(models.Model):
    entry = models.ForeignKey(QueueEntry, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    value = models.SmallIntegerField()  # +1 / -1

    class Meta:
        db_table = "session_votes"
        constraints = [
            models.UniqueConstraint(fields=["entry", "user"], name="session_vote_once"),
            models.CheckConstraint(condition=Q(value__in=[1, -1]), name="session_vote_value"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.value:+d}"
