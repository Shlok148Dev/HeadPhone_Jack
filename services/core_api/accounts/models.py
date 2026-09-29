"""Accounts, privacy settings and consents (Technical Bible 3.1, 9.2; SRS EP-01, EP-02)."""

import uuid

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

from .validators import validate_username


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class JingleUserManager(UserManager):
    def create_user(self, username=None, email=None, password=None, **extra_fields):
        email = self.normalize_email(email or "").lower()
        return super().create_user(username.lower(), email, password, **extra_fields)

    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        email = self.normalize_email(email or "").lower()
        return super().create_superuser(username.lower(), email, password, **extra_fields)


class User(AbstractUser, TimeStamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # JNG-12-07: 3-20 chars of [a-z0-9_.], case-insensitive unique (Lower() constraint below).
    username = models.CharField(max_length=20, validators=[validate_username])
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=60, blank=True)
    birth_year = models.PositiveSmallIntegerField(null=True, blank=True)
    college = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=80, blank=True)
    discoverable = models.BooleanField(default=False)
    private_until = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    # Google account subject (JNG-01-01 Google sign-in). Never sent to clients.
    google_sub = models.CharField(max_length=255, null=True, blank=True, unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = JingleUserManager()

    class Meta:
        db_table = "users"
        constraints = [
            models.UniqueConstraint(Lower("username"), name="users_username_ci_unique"),
        ]

    def __str__(self) -> str:
        return self.username

    @property
    def needs_onboarding(self) -> bool:
        """Google sign-ups must still give a birth year (18+ gate) before feed access."""
        return self.birth_year is None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class ActivityVisibility(models.TextChoices):
    FRIENDS = "friends"
    CIRCLES = "circles"
    NOBODY = "nobody"


class PrivacySettings(TimeStamped):
    """JNG-02-05/06. 1:1 with users; created at sign-up."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="privacy")
    activity_visibility = models.CharField(
        max_length=10, choices=ActivityVisibility.choices, default=ActivityVisibility.FRIENDS
    )
    show_last_active = models.BooleanField(default=True)
    concerts_visible = models.BooleanField(default=False)  # BR-10

    class Meta:
        db_table = "privacy_settings"
        verbose_name_plural = "privacy settings"

    def __str__(self) -> str:
        return f"privacy({self.user_id})"

    @classmethod
    def for_user(cls, user) -> "PrivacySettings":
        cached = getattr(user, "_privacy_cache", None)
        if cached is not None:
            return cached
        obj, _ = cls.objects.get_or_create(user=user)
        obj.user = user  # share the caller's instance so later edits to it are visible
        try:
            user._privacy_cache = obj
        except AttributeError:  # pragma: no cover - non-model stand-ins
            pass
        return obj


class ConsentPurpose(models.TextChoices):
    """NFR-PRIV-01: itemised purposes, each withdrawable as easily as given."""

    CORE_SERVICE = "core_service"
    ACTIVITY_SHARING = "activity_sharing"
    SUGGESTIONS_DISCOVERABILITY = "suggestions_discoverability"
    CONTACT_MATCHING = "contact_matching"
    PUSH_NOTIFICATIONS = "push_notifications"
    EMAIL_DIGEST = "email_digest"


CONSENT_DESCRIPTIONS: dict[str, str] = {
    ConsentPurpose.CORE_SERVICE: (
        "Run your Jingle account: sign-in, your profile and showing your listening to people you "
        "choose. Needed to use Jingle; to stop, delete your account."
    ),
    ConsentPurpose.ACTIVITY_SHARING: (
        "Share what you play with your friends and circles, as set in your privacy settings."
    ),
    ConsentPurpose.SUGGESTIONS_DISCOVERABILITY: (
        "Let Jingle suggest you to people who share friends or taste with you."
    ),
    ConsentPurpose.CONTACT_MATCHING: (
        "Find friends from your contacts. Contacts are hashed on your device and never uploaded."
    ),
    ConsentPurpose.PUSH_NOTIFICATIONS: "Send notifications to this browser.",
    ConsentPurpose.EMAIL_DIGEST: "Email you a short digest of what your friends played.",
}

REQUIRED_PURPOSES = frozenset({ConsentPurpose.CORE_SERVICE})


class Consent(TimeStamped):
    """One row per grant. Withdrawal stamps ``withdrawn_at``; a later grant adds a new row, so the
    table is an audit trail of the user's choices (Technical Bible 9.2)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="consents")
    purpose = models.CharField(max_length=40, choices=ConsentPurpose.choices)
    version = models.CharField(max_length=20)
    given_at = models.DateTimeField(default=timezone.now)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "consents"
        ordering = ["-given_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "purpose"],
                condition=Q(withdrawn_at__isnull=True),
                name="consents_one_active_per_purpose",
            )
        ]

    def __str__(self) -> str:
        state = "withdrawn" if self.withdrawn_at else "given"
        return f"{self.purpose} v{self.version} ({state})"

    @property
    def is_active(self) -> bool:
        return self.withdrawn_at is None
