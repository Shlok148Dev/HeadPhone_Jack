"""A suspended account can still read its own status, appeal and sign out (JNG-12-03/08)."""

from rest_framework.permissions import BasePermission

ALLOWED_WHILE_SUSPENDED = ("/api/v1/me/moderation", "/api/v1/auth/")


class NotSuspended(BasePermission):
    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return True
        path = request.path
        if path.startswith(ALLOWED_WHILE_SUSPENDED) or (
            path == "/api/v1/me" and request.method == "GET"
        ):
            return True
        from .services import require_not_suspended

        require_not_suspended(user)
        return True
