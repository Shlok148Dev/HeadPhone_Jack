"""Ingestion-domain tables (Tech Bible 3.1; ADR-0006).

Django owns the migrations; **ingest-ml writes these tables** (SQLAlchemy Core) and core-api only
reads them. Do not write to these models from core-api views or tasks, except the account-deletion
workflow, which deletes a user's rows.
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SourceKind(models.TextChoices):
    LISTENBRAINZ = "LISTENBRAINZ"
    LASTFM = "LASTFM"
    APPLE_MUSIC = "APPLE_MUSIC"
    SPOTIFY = "SPOTIFY"
    AMAZON_MUSIC = "AMAZON_MUSIC"
    YOUTUBE_EXPORT = "YOUTUBE_EXPORT"
    COMPANION = "COMPANION"


class Platform(models.TextChoices):
    SPOTIFY = "SPOTIFY"
    APPLE_MUSIC = "APPLE_MUSIC"
    AMAZON_MUSIC = "AMAZON_MUSIC"
    YOUTUBE_MUSIC = "YOUTUBE_MUSIC"
    UNKNOWN = "UNKNOWN"


class SourceStatus(models.TextChoices):
    CONNECTED = "CONNECTED"
    NEEDS_REAUTH = "NEEDS_REAUTH"
    PENDING_FIRST_PLAY = "PENDING_FIRST_PLAY"
    ERROR = "ERROR"
    DISABLED = "DISABLED"


class PlatformConnection(TimeStamped):
    """What the user sees: one row per music platform they pressed "Connect" for (BR-13).

    The Connection Orchestrator attaches one or more routes (LinkedSource rows) behind it.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="connections")
    platform = models.CharField(max_length=20, choices=Platform.choices)
    status = models.CharField(max_length=24, choices=SourceStatus.choices, default=SourceStatus.PENDING_FIRST_PLAY)
    first_play_at = models.DateTimeField(null=True, blank=True)
    last_signal_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "platform_connections"
        constraints = [models.UniqueConstraint(fields=["user", "platform"], name="platform_connection_unique")]


class LinkedSource(TimeStamped):
    """A route (Via) behind a platform connection. Never shown to users (BR-14)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="linked_sources")
    kind = models.CharField(max_length=20, choices=SourceKind.choices)
    external_user_id = models.CharField(max_length=200, blank=True)
    token_ciphertext = models.TextField(blank=True)
    token_key_id = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=24, choices=SourceStatus.choices, default=SourceStatus.CONNECTED)
    last_ok_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "linked_sources"
        constraints = [models.UniqueConstraint(fields=["user", "kind"], name="linked_source_user_kind")]


class ScrobbleToken(TimeStamped):
    """Per-user token for the ListenBrainz-compatible push endpoint. Only the SHA-256 is stored."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scrobble_tokens")
    token_sha256 = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=60, default="Jingle Companion")
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "scrobble_tokens"


class Artist(TimeStamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mbid = models.UUIDField(null=True, blank=True)
    name = models.CharField(max_length=300)

    class Meta:
        db_table = "artists"
        constraints = [
            models.UniqueConstraint(fields=["mbid"], condition=Q(mbid__isnull=False), name="artists_mbid")
        ]


class ArtistTag(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="tags")
    tag = models.CharField(max_length=80)
    weight = models.FloatField(default=1.0)

    class Meta:
        db_table = "artist_tags"
        constraints = [models.UniqueConstraint(fields=["artist", "tag"], name="artist_tag_unique")]


class Recording(TimeStamped):
    """Canonical track across platforms (SRS 4.4)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    isrc = models.CharField(max_length=12, null=True, blank=True)
    mbid = models.UUIDField(null=True, blank=True)
    title = models.CharField(max_length=500)
    artist_name = models.CharField(max_length=500)
    album = models.CharField(max_length=500, blank=True)
    release_mbid = models.UUIDField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    artwork_url = models.URLField(max_length=800, blank=True)
    artist = models.ForeignKey(Artist, null=True, blank=True, on_delete=models.SET_NULL, related_name="recordings")
    # normalised "artist|title" key used for fuzzy de-duplication before MusicBrainz resolution
    norm_key = models.CharField(max_length=600, db_index=True)
    resolution = models.CharField(max_length=16, default="unresolved")  # isrc | mbid | fuzzy | unresolved

    class Meta:
        db_table = "recordings"
        constraints = [
            models.UniqueConstraint(fields=["isrc"], condition=Q(isrc__isnull=False), name="recordings_isrc"),
            models.UniqueConstraint(fields=["mbid"], condition=Q(mbid__isnull=False), name="recordings_mbid"),
        ]


class RecordingLink(models.Model):
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE, related_name="links")
    platform = models.CharField(max_length=20, choices=Platform.choices)
    external_id = models.CharField(max_length=200, blank=True)
    url = models.URLField(max_length=800)
    # True when this is a platform search URL rather than a verified track link (JNG-06-03)
    is_search = models.BooleanField(default=False)

    class Meta:
        db_table = "recording_links"
        constraints = [
            models.UniqueConstraint(fields=["recording", "platform"], name="recording_link_platform")
        ]
