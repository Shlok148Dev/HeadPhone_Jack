from django.contrib import admin

from .models import FeatureFlag


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ("name", "enabled", "public", "note", "updated_at")
    list_editable = ("enabled",)
    search_fields = ("name",)
