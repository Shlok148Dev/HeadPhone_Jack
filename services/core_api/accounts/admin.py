from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Consent, PrivacySettings, User


class PrivacyInline(admin.StackedInline):
    model = PrivacySettings
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-created_at",)
    list_display = ("username", "display_name", "is_active", "is_staff", "created_at", "deleted_at")
    list_filter = ("is_active", "is_staff", "discoverable")
    search_fields = ("username", "display_name")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "last_login", "date_joined")
    inlines = [PrivacyInline]
    fieldsets = (
        (None, {"fields": ("id", "email", "username", "password")}),
        ("Profile", {"fields": ("display_name", "birth_year", "college", "city", "discoverable",
                                "private_until")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups",
                                    "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined", "created_at", "updated_at",
                              "deleted_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",),
                "fields": ("email", "username", "password1", "password2")}),
    )


@admin.register(Consent)
class ConsentAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "version", "given_at", "withdrawn_at")
    list_filter = ("purpose", "version")
    raw_id_fields = ("user",)
    readonly_fields = ("user", "purpose", "version", "given_at", "withdrawn_at")
