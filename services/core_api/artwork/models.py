"""Real artwork cache (docs/ux/DECISIONS.md D-ART-*): URLs and colours only, never image files."""

from django.db import models


class Kind(models.TextChoices):
    TRACK = "track"
    ARTIST = "artist"


class Artwork(models.Model):
    kind = models.CharField(max_length=8, choices=Kind.choices)
    key = models.CharField(max_length=600)  # normalised "artist|title", or artist name
    status = models.CharField(max_length=8, default="pending")  # found | missing | pending
    source = models.CharField(max_length=24, blank=True)  # itunes | coverartarchive | spotify
    url = models.URLField(max_length=800, blank=True)  # large (600 px)
    url_small = models.URLField(max_length=800, blank=True)  # 100 px, for lists and colour
    colors = models.JSONField(default=dict)  # {dominant, accent, ambient_dark, ambient_light}
    source_id = models.CharField(max_length=80, blank=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "artwork_cache"
        constraints = [models.UniqueConstraint(fields=["kind", "key"], name="artwork_kind_key")]

    def __str__(self) -> str:
        return f"{self.kind}:{self.key} ({self.status})"
