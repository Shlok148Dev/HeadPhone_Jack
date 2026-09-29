from rest_framework.permissions import BasePermission

from core_api.errors import ApiError


class IsOnboarded(BasePermission):
    """Feed access needs a birth year on file (18+ gate for Google sign-ups, NFR-PRIV-02)."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        if user and user.is_authenticated and user.needs_onboarding:
            raise ApiError(
                "ONBOARDING_REQUIRED", "Finish setting up your profile to continue.", 403
            )
        return True
