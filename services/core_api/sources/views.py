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


def delete_ingest_data(user_id) -> bool:
    """Ask ingest-ml to revoke push tokens and erase listens/live state (DPDP; SEC M5).

    Returns False (and logs) when ingest-ml is unreachable; callers that must guarantee erasure
    (``purge_account``) raise so Celery retries.
    """
    url = f"{settings.INGEST_INTERNAL_URL.rstrip('/')}/internal/users/{user_id}/data"
    try:
        resp = httpx.delete(
            url, headers={"X-Service-Token": settings.SERVICE_TOKEN}, timeout=INGEST_TIMEOUT
        )
    except httpx.HTTPError:
        log.warning("ingest-ml unreachable for data deletion")
        return False
    if resp.status_code not in (200, 204):
        log.warning("ingest-ml data deletion failed", extra={"status": resp.status_code})
        return False
    return True


class CompanionTokenView(APIView):
    """JNG-01-13: issue a Jingle Companion push token. Shown once; only its hash is stored."""

    @extend_schema(
        tags=["sources"],
        request=None,
        responses={
            201: inline_serializer("CompanionToken", {"token": serializers.CharField()}),
            409: err("CONSENT_REQUIRED"),
            429: err("RATE_LIMITED"),
            502: err("UPSTREAM_UNAVAILABLE"),
        },
    )
    @ratelimit(key="user", rate="10/h", scope="sources.companion_token")
    def post(self, request):
        from accounts.models import ConsentPurpose
        from accounts.services import active_consent

        # Collecting listening activity needs its own consent (NFR-PRIV-01, DPDP).
        if active_consent(request.user, ConsentPurpose.ACTIVITY_SHARING) is None:
            raise ApiError(
                "CONSENT_REQUIRED",
                "Allow Jingle to share what you play with your friends to connect this browser.",
                409,
                {"purpose": ConsentPurpose.ACTIVITY_SHARING},
            )
        data = ingest_post("/internal/scrobble-tokens", {"user_id": str(request.user.pk)})
        token = data.get("token") if isinstance(data, dict) else None
        if not token:
            raise ApiError(
                "UPSTREAM_UNAVAILABLE", "That didn't work. Please try again in a moment.", 502
            )
        resp = Response({"token": token}, status=status.HTTP_201_CREATED)
        resp["Cache-Control"] = "no-store"
        return resp
