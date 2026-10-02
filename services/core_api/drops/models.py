"""Daily Drop (JNG-14-01): one song a day per person, revealed to friends who dropped too."""

import uuid

from django.conf import settings
from django.db import models

NOTE_MAX = 140


class Drop(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="drops"
    )
    # The dropper's local calendar day (their notification timezone), so "today" means their today.
    day = models.DateField()
    recording = models.ForeignKey(
        "sources.Recording", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    title = models.CharField(max_length=500)
    artist = models.CharField(max_length=500)
    note = models.CharField(max_length=NOTE_MAX, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "day"], name="one_drop_per_day")]
        indexes = [models.Index(fields=["day", "user"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user_id} {self.day}: {self.title}"
