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


urlpatterns = [
    path("users/<uuid:user_id>/friends", UserFriendsView.as_view(), name="internal-user-friends"),
]
