"""Sends and mixtapes (Tech Bible 3.1 "Sharing"; EP-06; ADR-0020).

One ``Recommendation`` per send, 1 item (track) or 5–8 (mixtape), one ``Delivery`` per recipient
carrying that person's Sent → Delivered → Viewed → Played status.
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

NOTE_MAX = 280  # JNG-06-01
MIXTAPE_MIN, MIXTAPE_MAX = 5, 8  # JNG-06-02
MAX_RECIPIENTS = 50
REACTIONS = ("🔥", "❤️", "😂", "🤯", "👀", "🙌")  # JNG-06-06
PLAYED_WINDOW_DAYS = 30  # a play counts if it happens within 30 days of the send
CREDIT_WINDOW_DAYS = 60  # Tech Bible 6.4


class Kind(models.TextChoices):
    TRACK = "track"
    MIXTAPE = "mixtape"


class Recommendation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sends"
    )
    kind = models.CharField(max_length=8, choices=Kind.choices)
    note = models.CharField(max_length=NOTE_MAX, blank=True)
    reply_to = models.ForeignKey(
        "Delivery", null=True, blank=True, on_delete=models.SET_NULL, related_name="replies"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recommendations"
        indexes = [models.Index(fields=["sender", "-created_at"], name="recs_sender")]

    def __str__(self) -> str:
        return f"{self.kind} from {self.sender_id}"


class Item(models.Model):
    """A song in a send. ``recording`` is null when the song isn't resolved yet; title and
    artist are what the sender shared (ADR-0020), never artwork or IDs from Spotify's API."""

    rec = models.ForeignKey(Recommendation, on_delete=models.CASCADE, related_name="items")
    position = models.PositiveSmallIntegerField()
    recording = models.ForeignKey(
        "sources.Recording", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    title = models.CharField(max_length=500)
    artist = models.CharField(max_length=500)

    class Meta:
        db_table = "recommendation_items"
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["rec", "position"], name="rec_item_position")
        ]

    def __str__(self) -> str:
        return f"{self.artist} - {self.title}"


class Delivery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rec = models.ForeignKey(Recommendation, on_delete=models.CASCADE, related_name="deliveries")
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received"
    )
    circle = models.ForeignKey(
        "circles.Circle", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    delivered_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    played_at = models.DateTimeField(null=True, blank=True)
    reaction = models.CharField(max_length=8, blank=True)
    reacted_at = models.DateTimeField(null=True, blank=True)
    credit_artist = models.CharField(max_length=500, blank=True)  # JNG-06-05
    credited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "recommendation_deliveries"
        constraints = [models.UniqueConstraint(fields=["rec", "recipient"], name="delivery_once")]
        indexes = [
            models.Index(fields=["recipient", "-delivered_at"], name="deliveries_recipient"),
            models.Index(
                fields=["recipient"],
                condition=Q(played_at__isnull=True),
                name="deliveries_unplayed",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.rec_id} to {self.recipient_id}: {self.status}"

    @property
    def status(self) -> str:
        if self.played_at:
            return "played"
        if self.viewed_at:
            return "viewed"
        if self.delivered_at:
            return "delivered"
        return "sent"
