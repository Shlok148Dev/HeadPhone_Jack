"""Rituals: weekly song battles per circle and the monthly recap (EP-09; ADR-0023)."""

import uuid

from django.conf import settings
from django.db import models

VOTES_PER_WEEK = 3  # JNG-09-02
SEASON_WEEKS = 8  # JNG-09-04


class Battle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey("circles.Circle", on_delete=models.CASCADE, related_name="battles")
    week = models.DateField()  # Monday (IST) of the battle's week
    nominate_opens = models.DateTimeField()
    vote_opens = models.DateTimeField()
    closes_at = models.DateTimeField()
    skipped = models.BooleanField(default=False)  # JNG-09-08: doesn't count towards the season
    results = models.JSONField(null=True, blank=True)  # set by the close job (JNG-09-03)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "battles"
        constraints = [models.UniqueConstraint(fields=["circle", "week"], name="battle_week_once")]

    def __str__(self) -> str:
        return f"{self.circle_id} {self.week}"


class Nomination(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    battle = models.ForeignKey(Battle, on_delete=models.CASCADE, related_name="nominations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    recording = models.ForeignKey(
        "sources.Recording", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    title = models.CharField(max_length=500)
    artist = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "battle_nominations"
        constraints = [
            models.UniqueConstraint(fields=["battle", "user"], name="one_nomination_per_week")
        ]

    def __str__(self) -> str:
        return f"{self.artist} - {self.title}"


class BattleVote(models.Model):
    battle = models.ForeignKey(Battle, on_delete=models.CASCADE, related_name="votes")
    nomination = models.ForeignKey(Nomination, on_delete=models.CASCADE, related_name="votes")
    voter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "battle_votes"
        constraints = [
            models.UniqueConstraint(fields=["nomination", "voter"], name="battle_vote_once")
        ]

    def __str__(self) -> str:
        return f"{self.voter_id} -> {self.nomination_id}"


class Recap(models.Model):
    """JNG-09-05: one per member per month; shareable only by explicit choice (JNG-09-06)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recaps"
    )
    month = models.CharField(max_length=7)  # YYYY-MM
    data = models.JSONField()
    share_token = models.CharField(max_length=32, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recaps"
        constraints = [models.UniqueConstraint(fields=["user", "month"], name="recap_month_once")]

    def __str__(self) -> str:
        return f"{self.user_id} {self.month}"
