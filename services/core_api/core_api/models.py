"""Platform-wide models owned by core_api itself."""

import uuid

from django.db import models


class FeatureFlag(models.Model):
    """Runtime feature switch (Technical Bible 3.1 ``feature_flags``; BR-11)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.SlugField(max_length=80, unique=True)
    enabled = models.BooleanField(default=False)
    public = models.BooleanField(
        default=True, help_text="Exposed to browsers via GET /api/v1/flags."
    )
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "feature_flags"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name}={'on' if self.enabled else 'off'}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from .flags import invalidate

        invalidate()

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        from .flags import invalidate

        invalidate()
        return result
