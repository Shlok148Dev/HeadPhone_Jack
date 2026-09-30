"""Service-to-service routes under ``/internal/`` (CONTRACTS.md §3). The edge never exposes them."""

from __future__ import annotations

import hmac

from django.conf import settings
from django.urls import path
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView


class HasServiceToken(BasePermission):
    """Allows the request only with a valid ``X-Service-Token`` header."""

    def has_permission(self, request, view) -> bool:
        supplied = request.headers.get("X-Service-Token", "")
        expected = settings.SERVICE_TOKEN or ""
        return bool(expected) and hmac.compare_digest(supplied.encode(), expected.encode())


class InternalView(APIView):
    authentication_classes: list = []
    permission_classes = [HasServiceToken]


@extend_schema(exclude=True)
class UserFriendsView(InternalView):
    """Friend ids of a user, for the realtime gateway's rooms (CONTRACTS.md §9)."""

    def get(self, request, user_id):
        from circles.services import co_member_ids
        from social.services import blocked_ids, friend_ids

        # Everyone whose card this user can see live: friends and circle co-members (not blocked).
        ids = (set(friend_ids(user_id)) | co_member_ids(user_id)) - blocked_ids(user_id)
        return Response(sorted(str(f) for f in ids))


class SessionMemberView(InternalView):
    """Realtime asks before joining a socket to `session:{id}` (Tech Bible 4.3)."""

    @extend_schema(exclude=True)
    def get(self, request, session_id, user_id):
        from core_api.policy import is_blocked_either_way
        from listening.models import ListeningSession

        s = ListeningSession.objects.filter(pk=session_id, ended_at__isnull=True).first()
        ok = bool(
            s
            and s.participants.filter(
                user_id=user_id, joined_at__isnull=False, left_at__isnull=True
            ).exists()
            and not is_blocked_either_way(user_id, s.host_id)
        )
        return Response({"ok": ok}, status=200 if ok else 404)


urlpatterns = [
    path("users/<uuid:user_id>/friends", UserFriendsView.as_view(), name="internal-user-friends"),
    path(
        "sessions/<uuid:session_id>/members/<uuid:user_id>",
        SessionMemberView.as_view(),
        name="internal-session-member",
    ),
]
