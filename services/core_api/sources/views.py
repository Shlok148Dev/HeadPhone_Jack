"""Sources proxy to ingest-ml (ADR-0006). The browser never calls ingest-ml directly."""

from __future__ import annotations

import logging

import httpx
from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core_api.errors import ApiError
from core_api.ratelimit import ratelimit
from core_api.schema import err

log = logging.getLogger(__name__)

INGEST_TIMEOUT = httpx.Timeout(5.0, connect=2.0)


def ingest_post(path: str, payload: dict) -> dict:
    """POST to ingest-ml ``/internal/*`` with the service token."""
    url = f"{settings.INGEST_INTERNAL_URL.rstrip('/')}{path}"
    try:
        resp = httpx.post(
            url,
            json=payload,
            headers={"X-Service-Token": settings.SERVICE_TOKEN},
            timeout=INGEST_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        log.warning("ingest-ml unreachable", extra={"path": path})
        raise ApiError(
            "UPSTREAM_UNAVAILABLE", "That didn't work. Please try again in a moment.", 502
        ) from exc
    if resp.status_code >= 400:
        log.warning("ingest-ml error", extra={"path": path, "status": resp.status_code})
        raise ApiError(
            "UPSTREAM_UNAVAILABLE", "That didn't work. Please try again in a moment.", 502
        )
    try:
        return resp.json()
    except ValueError as exc:
        raise ApiError(
            "UPSTREAM_UNAVAILABLE", "That didn't work. Please try again in a moment.", 502
        ) from exc


class CompanionTokenView(APIView):
    """JNG-01-13: issue a Jingle Companion push token. Shown once; only its hash is stored."""

    @extend_schema(
        tags=["sources"],
        request=None,
        responses={
            201: inline_serializer("CompanionToken", {"token": serializers.CharField()}),
            429: err("RATE_LIMITED"),
            502: err("UPSTREAM_UNAVAILABLE"),
        },
    )
    @ratelimit(key="user", rate="10/h", scope="sources.companion_token")
    def post(self, request):
        data = ingest_post("/internal/scrobble-tokens", {"user_id": str(request.user.pk)})
        token = data.get("token") if isinstance(data, dict) else None
        if not token:
            raise ApiError(
                "UPSTREAM_UNAVAILABLE", "That didn't work. Please try again in a moment.", 502
            )
        resp = Response({"token": token}, status=status.HTTP_201_CREATED)
        resp["Cache-Control"] = "no-store"
        return resp
