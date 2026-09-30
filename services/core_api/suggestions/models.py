"""Suggestions data (Tech Bible 3.1 ``suggestion_feedback``; JNG-03-05, JNG-03-07)."""

import uuid

from django.conf import settings
from django.db import models


class TasteSeed(models.Model):
    """Onboarding picks that give a new member a provisional taste (Tech Bible 5.3 cold start)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="taste_seed",
    )
    artists = models.JSONField(default=list, blank=True)
    genres = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "taste_seeds"

    def __str__(self) -> str:
        return f"taste seed {self.user_id}"


class FeedbackAction(models.TextChoices):
    SHOWN = "shown"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"


class SuggestionFeedback(models.Model):
    """Training labels for the future ranker and the 90-day dismiss rule."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    action = models.CharField(max_length=12, choices=FeedbackAction.choices)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "suggestion_feedback"
        indexes = [models.Index(fields=["user", "action", "at"], name="sugfb_user_action_at")]

    def __str__(self) -> str:
        return f"{self.action} {self.candidate_id}"
