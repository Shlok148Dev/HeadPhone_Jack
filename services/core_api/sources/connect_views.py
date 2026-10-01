"""Jingle Connect endpoints (BR-13–15; ADR-0003, ADR-0006). core-api decides who may connect
(consents, allowlist, flags) and ingest-ml decides how (the Connection Orchestrator)."""

from __future__ import annotations

import logging
from urllib.parse import urlencode

import httpx
from django.conf import settings
from django.shortcuts import redirect
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import ConsentPurpose
from accounts.services import active_consent
from core_api import flags
from core_api.errors import ApiError
from core_api.ratelimit import ratelimit
from core_api.schema import err

log = logging.getLogger(__name__)

PLATFORMS = ("SPOTIFY", "APPLE_MUSIC", "YOUTUBE_MUSIC", "AMAZON_MUSIC")
TIMEOUT = httpx.Timeout(10.0, connect=2.0)
UPLOAD_TIMEOUT = httpx.Timeout(120.0, connect=5.0)
MAX_UPLOAD = 50 * 1024 * 1024
UNAVAILABLE = "That didn't work. Please try again in a moment."


def _ingest(method: str, path: str, *, passthrough: tuple[int, ...] = (400, 404, 413), **kw):
    """Call ingest-ml ``/internal/*``; user-safe 4xx errors pass through, anything else is 502."""
    url = f"{settings.INGEST_INTERNAL_URL.rstrip('/')}{path}"
    try:
        resp = httpx.request(
            method,
            url,
            headers={"X-Service-Token": settings.SERVICE_TOKEN},
            timeout=kw.pop("timeout", TIMEOUT),
            **kw,
        )
    except httpx.HTTPError as exc:
        raise ApiError("UPSTREAM_UNAVAILABLE", UNAVAILABLE, 502) from exc
    if resp.status_code in passthrough:
        try:
            e = resp.json()["error"]
            raise ApiError(e["code"], e["message"], resp.status_code)
        except (ValueError, KeyError, TypeError):
            raise ApiError("UPSTREAM_UNAVAILABLE", UNAVAILABLE, 502) from None
    if resp.status_code >= 400:
        log.warning("ingest-ml error", extra={"path": path, "status": resp.status_code})
        raise ApiError("UPSTREAM_UNAVAILABLE", UNAVAILABLE, 502)
    return resp.json() if resp.content else None


def remove_route(user_id, kind: str) -> bool:
    """Best-effort route removal after consent withdrawal; logs instead of raising."""
    try:
        _ingest("DELETE", f"/internal/sources/{user_id}/{kind}")
        return True
    except ApiError:
        log.warning("route removal failed after consent withdrawal")
        return False


def _require(user, purpose: str, message: str) -> None:
    if active_consent(user, purpose) is None:
        raise ApiError("CONSENT_REQUIRED", message, 409, {"purpose": purpose})


def _platform(value: str) -> str:
    value = value.upper()
    if value not in PLATFORMS:
        raise ApiError("NOT_FOUND", "Unknown music app.", 404)
    return value


def _allowlisted(user) -> bool:
    from moderation.services import allowlist_emails

    allow = {e.strip().lower() for e in settings.SPOTIFY_ALLOWLIST.split(",") if e.strip()}
    return user.email.lower() in allow | allowlist_emails()  # .env + admin console (JNG-12-06)


def _flag_values() -> dict[str, bool]:
    return {name: f["enabled"] for name, f in flags.all_flags().items()}


SHARING_MSG = "Allow Jingle to share what you play with your friends to connect your music."
PlanSerializer = inline_serializer(
    "ConnectPlan",
    {
        "action": serializers.ChoiceField(choices=["redirect", "lastfm_then_spotify", "browser"]),
        "url": serializers.URLField(allow_null=True),
        "live_on_phone": serializers.BooleanField(),
    },
)


class ConnectStartView(APIView):
    """JNG-01-14: one button per platform; the orchestrator picks the route (BR-13)."""

    @extend_schema(
        tags=["sources"],
        request=None,
        responses={200: PlanSerializer, 404: err("NOT_FOUND"), 409: err("CONSENT_REQUIRED")},
    )
    @ratelimit(key="user", rate="30/h", scope="sources.connect")
    def post(self, request, platform: str):
        platform = _platform(platform)
        _require(request.user, ConsentPurpose.ACTIVITY_SHARING, SHARING_MSG)
        plan = _ingest(
            "POST",
            "/internal/connect/start",
            json={
                "user_id": str(request.user.pk),
                "platform": platform,
                "allowlisted": _allowlisted(request.user),
                "flags": _flag_values(),
            },
        )
        if plan.get("action") == "lastfm_then_spotify":
            _require(
                request.user,
                ConsentPurpose.LASTFM_LINK,
                "Allow Jingle to read what you play from Last.fm to connect Spotify on every "
                "device.",
            )
        return Response(plan)


def _back_to_app(**query: str):
    return redirect(
        f"{settings.PUBLIC_BASE_URL.rstrip('/')}/settings/connections?{urlencode(query)}"
    )


class SpotifyCallbackView(APIView):
    """Spotify's redirect target. State-bound (no cookies needed; ADR-0016)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["sources"],
        parameters=[OpenApiParameter("state", str), OpenApiParameter("code", str)],
        responses={302: None},
    )
    def get(self, request):
        state, code = request.GET.get("state", ""), request.GET.get("code", "")
        if request.GET.get("error") or not state or not code:
            return _back_to_app(error="cancelled", platform="SPOTIFY")
        try:
            _ingest(
                "POST",
                "/internal/connect/spotify/callback",
                json={"state": state[:200], "code": code[:2000]},
            )
        except ApiError as exc:
            return _back_to_app(error=exc.code.lower(), platform="SPOTIFY")
        return _back_to_app(connected="SPOTIFY")


class LastfmCallbackView(APIView):
    """Last.fm's web-auth callback (``?state=…&token=…``)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["sources"],
        parameters=[OpenApiParameter("state", str), OpenApiParameter("token", str)],
        responses={302: None},
    )
    def get(self, request):
        state, token = request.GET.get("state", ""), request.GET.get("token", "")
        if not state or not token:
            return _back_to_app(error="cancelled", platform="SPOTIFY")
        try:
            data = _ingest(
                "POST",
                "/internal/connect/lastfm/callback",
                json={"state": state[:200], "token": token[:200]},
            )
        except ApiError as exc:
            return _back_to_app(error=exc.code.lower())
        return _back_to_app(
            connected=str(data.get("platform", "SPOTIFY")), then="link_spotify_lastfm"
        )


class ListenBrainzLinkView(APIView):
    """JNG-01-02 "Other ways to connect": paste a ListenBrainz user token."""

    @extend_schema(
        tags=["sources"],
        request=inline_serializer(
            "LinkListenBrainz",
            {
                "platform": serializers.ChoiceField(choices=PLATFORMS),
                "token": serializers.CharField(max_length=200),
            },
        ),
        responses={201: None, 400: err("TOKEN_INVALID"), 409: err("CONSENT_REQUIRED")},
    )
    @ratelimit(key="user", rate="20/h", scope="sources.listenbrainz")
    def post(self, request):
        platform = _platform(str(request.data.get("platform", "")))
        token = str(request.data.get("token", "")).strip()
        _require(request.user, ConsentPurpose.ACTIVITY_SHARING, SHARING_MSG)
        if not token:
            raise ApiError(
                "TOKEN_INVALID",
                "That token didn't work — copy it again from ListenBrainz settings",
                400,
            )
        _ingest(
            "POST",
            "/internal/connect/listenbrainz",
            json={"user_id": str(request.user.pk), "platform": platform, "token": token[:200]},
        )
        return Response(status=status.HTTP_201_CREATED)


class LastfmUsernameView(APIView):
    """Connect a public Last.fm profile by username (needs the ``lastfm_link`` consent)."""

    @extend_schema(
        tags=["sources"],
        request=inline_serializer(
            "LinkLastfm",
            {
                "platform": serializers.ChoiceField(choices=PLATFORMS),
                "username": serializers.CharField(max_length=64),
            },
        ),
        responses={201: None, 400: err("LASTFM_FAILED"), 409: err("CONSENT_REQUIRED")},
    )
    @ratelimit(key="user", rate="20/h", scope="sources.lastfm")
    def post(self, request):
        platform = _platform(str(request.data.get("platform", "")))
        _require(request.user, ConsentPurpose.ACTIVITY_SHARING, SHARING_MSG)
        _require(
            request.user,
            ConsentPurpose.LASTFM_LINK,
            "Allow Jingle to read what you play from Last.fm.",
        )
        _ingest(
            "POST",
            "/internal/connect/lastfm/username",
            json={
                "user_id": str(request.user.pk),
                "platform": platform,
                "username": str(request.data.get("username", "")).strip()[:64],
            },
        )
        return Response(status=status.HTTP_201_CREATED)


class UnlinkView(APIView):
    """JNG-01-09: disconnect one music app without affecting the others."""

    @extend_schema(tags=["sources"], responses={204: None, 404: err("NOT_FOUND")})
    def delete(self, request, platform: str):
        platform = _platform(platform)
        _ingest("DELETE", f"/internal/connections/{request.user.pk}/{platform}")
        return Response(status=status.HTTP_204_NO_CONTENT)


class YouTubeImportView(APIView):
    """JNG-01-06: upload a Google Takeout watch history (≤ 50 MB) → 202 + job id."""

    parser_classes = [MultiPartParser]

    @extend_schema(
        tags=["sources"],
        request={
            "multipart/form-data": inline_serializer(
                "TakeoutUpload", {"file": serializers.FileField()}
            )
        },
        responses={
            202: inline_serializer(
                "ImportJob", {"job_id": serializers.CharField(), "status": serializers.CharField()}
            ),
            400: err("VALIDATION_ERROR"),
            409: err("CONSENT_REQUIRED"),
            413: err("FILE_TOO_LARGE"),
        },
    )
    @ratelimit(key="user", rate="10/h", scope="imports.youtube")
    def post(self, request):
        _require(request.user, ConsentPurpose.ACTIVITY_SHARING, SHARING_MSG)
        upload = request.FILES.get("file")
        if upload is None:
            raise ApiError("VALIDATION_ERROR", "Choose your watch-history file first.", 400)
        if upload.size > MAX_UPLOAD:
            raise ApiError("FILE_TOO_LARGE", "That file is over 50 MB.", 413)
        data = _ingest(
            "POST",
            "/internal/imports/youtube",
            timeout=UPLOAD_TIMEOUT,
            data={"user_id": str(request.user.pk)},
            files={"file": ("upload", upload.file, "application/octet-stream")},
        )
        return Response(data, status=status.HTTP_202_ACCEPTED)


class ImportStatusView(APIView):
    @extend_schema(
        tags=["sources"],
        responses={
            200: inline_serializer(
                "ImportStatus",
                {
                    "status": serializers.CharField(),
                    "imported": serializers.IntegerField(),
                    "found": serializers.IntegerField(required=False),
                    "error": serializers.CharField(required=False),
                },
            ),
            404: err("NOT_FOUND"),
        },
    )
    def get(self, request, job_id: str):
        return Response(
            _ingest(
                "GET", f"/internal/imports/{job_id[:64]}", params={"user_id": str(request.user.pk)}
            )
        )
