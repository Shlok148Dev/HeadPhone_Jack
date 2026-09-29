"""Serializers for accounts, auth, privacy and consents. Explicit fields only; never ``birth_year``,
tokens or ``google_sub`` in output."""

from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from . import services
from .models import ActivityVisibility, ConsentPurpose, PrivacySettings, User
from .validators import validate_clean_text, validate_username


def _run(validator, value):
    try:
        validator(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc
    return value


class UsernameField(serializers.CharField):
    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", 20)
        kwargs.setdefault("min_length", 3)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data).strip().lower()
        return _run(validate_username, value)


class CleanTextField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data).strip()
        return _run(validate_clean_text, value)


class PrivateModeStateSerializer(serializers.Serializer):
    active = serializers.BooleanField()
    until = serializers.DateTimeField(
        allow_null=True, help_text="End of Private mode; null when off or 'until I turn it off'."
    )


class MeSerializer(serializers.ModelSerializer):
    """The signed-in user's own profile (JNG-01-01, JNG-01-12)."""

    needs_onboarding = serializers.BooleanField(read_only=True)
    private_mode = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "display_name",
            "college",
            "city",
            "discoverable",
            "needs_onboarding",
            "private_mode",
            "created_at",
        ]
        read_only_fields = fields

    def get_private_mode(self, obj) -> PrivateModeStateSerializer:
        return PrivateModeStateSerializer(services.private_mode_state(obj)).data


class MeUpdateSerializer(serializers.Serializer):
    display_name = CleanTextField(max_length=60, min_length=1, required=False)
    username = UsernameField(required=False)
    college = CleanTextField(max_length=120, allow_blank=True, required=False)
    city = CleanTextField(max_length=80, allow_blank=True, required=False)
    birth_year = serializers.IntegerField(
        min_value=1900, max_value=2100, required=False,
        help_text="Accepted only while not yet set (Google sign-up onboarding).",
    )

    def validate_username(self, value):
        user = self.context["request"].user
        if services.username_taken(value, exclude_id=user.pk):
            raise serializers.ValidationError("That username is taken.")
        return value


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, min_length=10, max_length=128)
    username = UsernameField()
    display_name = CleanTextField(max_length=60, required=False, allow_blank=True)
    birth_year = serializers.IntegerField(min_value=1900, max_value=2100)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_username(self, value):
        if services.username_taken(value):
            raise serializers.ValidationError("That username is taken.")
        return value

    def validate(self, attrs):
        probe = User(email=attrs["email"], username=attrs["username"])
        try:
            validate_password(attrs["password"], user=probe)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, max_length=128)


class GoogleSignInSerializer(serializers.Serializer):
    id_token = serializers.CharField(max_length=4096)


class AuthResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    user = MeSerializer()


class GoogleAuthResponseSerializer(AuthResponseSerializer):
    created = serializers.BooleanField()


class PrivacySerializer(serializers.ModelSerializer):
    """JNG-02-05 (precise last-active time), JNG-02-06 (Private mode)."""

    private_mode = serializers.SerializerMethodField()

    class Meta:
        model = PrivacySettings
        fields = ["activity_visibility", "show_last_active", "concerts_visible", "private_mode"]
        read_only_fields = fields

    def get_private_mode(self, obj) -> PrivateModeStateSerializer:
        return PrivateModeStateSerializer(services.private_mode_state(obj.user)).data


class PrivacyUpdateSerializer(serializers.Serializer):
    activity_visibility = serializers.ChoiceField(
        choices=ActivityVisibility.choices, required=False
    )
    show_last_active = serializers.BooleanField(required=False)
    concerts_visible = serializers.BooleanField(required=False)
    private_mode = serializers.ChoiceField(
        choices=[("1h", "1 hour"), ("8h", "8 hours"), ("until_off", "Until I turn it off"),
                 ("off", "Off")],
        required=False,
        help_text="Turn Private mode on for a duration, or off.",
    )


class ConsentItemSerializer(serializers.Serializer):
    purpose = serializers.ChoiceField(choices=ConsentPurpose.choices)
    description = serializers.CharField()
    required = serializers.BooleanField()
    given = serializers.BooleanField()
    version = serializers.CharField(allow_null=True)
    given_at = serializers.DateTimeField(allow_null=True)
    withdrawn_at = serializers.DateTimeField(allow_null=True)


class ConsentUpdateSerializer(serializers.Serializer):
    given = serializers.BooleanField()


class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(
        required=False, write_only=True,
        help_text="Required for accounts with a password.",
    )
    confirm = serializers.CharField(
        required=False, help_text="For Google-only accounts: type your username to confirm."
    )
