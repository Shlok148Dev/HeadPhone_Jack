"""Play a circle playlist in order in your own app (JNG-04-09, D-EXPORT-01).

The playlist is created in the listener's account by their browser (their app tokens never reach
Jingle). Jingle remembers only where it put the copy, and caches song matches it computed itself.
"""

from django.conf import settings
from django.db import models

PLATFORMS = ("spotify", "apple_music", "youtube_music")


class PlaylistExport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    circle = models.ForeignKey("circles.Circle", on_delete=models.CASCADE, related_name="+")
    platform = models.CharField(max_length=20)
    external_id = models.CharField(max_length=120)  # the playlist's id in that app
    url = models.URLField(max_length=300)
    track_keys = models.JSONField(default=list)  # the songs, in order, last exported
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "circle", "platform"], name="one_export_per_app"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.circle_id} {self.platform}"


class TrackMatch(models.Model):
    """A song's id in another catalogue, found by Jingle's own server-side search (never by
    clients, so the shared cache can't be poisoned). Only YouTube for now (quota-bound)."""

    platform = models.CharField(max_length=20)
    track_key = models.CharField(max_length=600)
    external_id = models.CharField(max_length=64, blank=True)  # "" = searched, not found
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["platform", "track_key"], name="one_match_per_song")
        ]

    def __str__(self) -> str:
        return f"{self.platform}:{self.track_key}"
