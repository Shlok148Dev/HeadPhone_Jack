"""Blends (Technical Bible 3.1 "Blends and sessions"; EP-07; ADR-0021)."""

import uuid

from django.conf import settings
from django.db import models


class Blend(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blends_created"
    )
    circle = models.ForeignKey(
        "circles.Circle", null=True, blank=True, on_delete=models.CASCADE, related_name="blends"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "blends"

    def __str__(self) -> str:
        return self.name


class BlendMember(models.Model):
    blend = models.ForeignKey(Blend, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")

    class Meta:
        db_table = "blend_members"
        constraints = [models.UniqueConstraint(fields=["blend", "user"], name="blend_member_once")]

    def __str__(self) -> str:
        return f"{self.user_id} in {self.blend_id}"


class BlendTrack(models.Model):
    blend = models.ForeignKey(Blend, on_delete=models.CASCADE, related_name="tracks")
    position = models.PositiveSmallIntegerField()
    recording = models.ForeignKey(
        "sources.Recording", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    title = models.CharField(max_length=500)
    artist = models.CharField(max_length=500)
    reason = models.CharField(max_length=200)  # required (Tech Bible 3.1)
    contributor_ids = models.JSONField(default=list)
    pinned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "blend_tracks"
        ordering = ["position"]

    def __str__(self) -> str:
        return f"{self.artist} - {self.title}"
