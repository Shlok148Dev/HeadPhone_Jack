"""Weekly charts (D-CHART-01): per-listener, per-local-day play counts, rebuilt hourly."""

from django.conf import settings
from django.db import models


class DailyPlays(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    day = models.DateField()  # the listener's local calendar day
    track_key = models.CharField(max_length=600)  # artwork.services.track_key: merges apps
    title = models.CharField(max_length=500)
    artist = models.CharField(max_length=500)  # display credit as played
    # [[artist_key, display_name, credit]]: primary 1.0, featured 0.5 (D-CHART-02).
    artists = models.JSONField(default=list)
    recording_id = models.UUIDField(null=True, blank=True)
    plays = models.PositiveIntegerField(default=0)
    first_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "day", "track_key"], name="one_row_per_user_day_track"
            )
        ]
        indexes = [models.Index(fields=["day", "user"])]

    def __str__(self) -> str:
        return f"{self.user_id} {self.day} {self.track_key} ×{self.plays}"


class ArtistFirstPlay(models.Model):
    """When a user first played an artist on Jingle: powers "new fans this week" without scans."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    artist_key = models.CharField(max_length=500)
    first_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "artist_key"], name="one_first_play_per_artist")
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.artist_key} {self.first_at:%Y-%m-%d}"
