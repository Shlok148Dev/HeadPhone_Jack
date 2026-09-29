from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import flags


def healthz(request):
    """Liveness + DB readiness for Compose health checks."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        db = "ok"
    except Exception:  # noqa: BLE001
        db = "down"
    return JsonResponse(
        {"status": "ok" if db == "ok" else "degraded", "db": db},
        status=200 if db == "ok" else 503,
    )


class FlagsView(APIView):
    """Public feature flags for the web app (BR-11: hidden integrations stay hidden)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["flags"],
        operation_id="flags_list",
        responses=inline_serializer(
            "PublicFlags",
            {
                "flags": serializers.DictField(child=serializers.BooleanField()),
                "google_signin_enabled": serializers.BooleanField(),
            },
        ),
    )
    def get(self, request):
        resp = Response(
            {
                "flags": flags.public_flags(),
                "google_signin_enabled": bool(settings.GOOGLE_OAUTH_CLIENT_ID),
            }
        )
        resp["Cache-Control"] = "public, max-age=30"
        return resp
