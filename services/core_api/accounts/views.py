"""The signed-in user's profile, privacy, consents and data rights."""

from __future__ import annotations

import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core_api import events
from core_api.errors import ApiError
from core_api.ratelimit import ratelimit
from core_api.schema import err

from . import services
from .auth_views import age_restricted
from .models import REQUIRED_PURPOSES, ConsentPurpose, PrivacySettings
from .serializers import (
    ConsentItemSerializer,
    ConsentUpdateSerializer,
    DeleteAccountSerializer,
    MeSerializer,
    MeUpdateSerializer,
    PrivacySerializer,
    PrivacyUpdateSerializer,
)
from .validators import is_old_enough


@extend_schema(exclude=True)
@api_view(["GET"])
@permission_classes([AllowAny])
def ping(request):
    return Response({"service": "core-api", "ok": True})


class MeView(APIView):
    """JNG-01-01 profile, JNG-01-12 onboarding fields, JNG-01-10 account deletion."""

    @extend_schema(tags=["me"], responses={200: MeSerializer, 401: err("UNAUTHENTICATED")})
    def get(self, request):
        resp = Response(MeSerializer(request.user).data)
        resp["Cache-Control"] = "private, no-store"
        return resp

    @extend_schema(
        tags=["me"],
        request=MeUpdateSerializer,
        responses={
            200: MeSerializer,
            400: err("VALIDATION_ERROR | BIRTH_YEAR_LOCKED"),
            403: err("AGE_RESTRICTED (account is removed)"),
        },
    )
    def patch(self, request):
        user = request.user
        ser = MeUpdateSerializer(data=request.data, context={"request": request}, partial=True)
        ser.is_valid(raise_exception=True)
        data = dict(ser.validated_data)
        if "birth_year" in data:
            if user.birth_year is not None:
                raise ApiError(
                    "BIRTH_YEAR_LOCKED", "Your birth year is already set.", 400,
                    details={"birth_year": ["Your birth year is already set."]},
                )
            if not is_old_enough(data["birth_year"]):
                # NFR-PRIV-02: no under-18 accounts. Remove the just-created (Google) account.
                with transaction.atomic():
                    services.revoke_all_tokens(user)
                    user.delete()
                raise age_restricted()
        for field, value in data.items():
            setattr(user, field, value)
        if data:
            user.save(update_fields=[*data.keys(), "updated_at"])
        return Response(MeSerializer(user).data)

    @extend_schema(
        tags=["me"],
        request=DeleteAccountSerializer,
        responses={
            202: OpenApiResponse(description="Account scheduled for deletion"),
            400: err("CONFIRMATION_REQUIRED"),
            403: err("CONFIRMATION_FAILED"),
        },
    )
    @ratelimit(key="user", rate="5/h", scope="me.delete")
    def delete(self, request):
        """JNG-01-10: delete my account. Hidden and anonymised now; purged within 30 days."""
        user = request.user
        ser = DeleteAccountSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        if user.has_usable_password():
            pw = ser.validated_data.get("password")
            if not pw:
                raise ApiError("CONFIRMATION_REQUIRED", "Enter your password to confirm.", 400)
            if not user.check_password(pw):
                raise ApiError("CONFIRMATION_FAILED", "That password is incorrect.", 403)
        else:
            if ser.validated_data.get("confirm", "").strip().lower() != user.username:
                raise ApiError("CONFIRMATION_REQUIRED", "Type your username to confirm.", 400)
        services.soft_delete_account(user)
        resp = Response(
            {"status": "scheduled", "purge_within_days": 30}, status=status.HTTP_202_ACCEPTED
        )
        services.clear_refresh_cookie(resp)
        return resp


class PrivacyView(APIView):
    """JNG-02-05 hide precise last-active time; JNG-02-06 Private mode (1 h, 8 h, until off)."""

    @extend_schema(tags=["me"], responses={200: PrivacySerializer})
    def get(self, request):
        return Response(PrivacySerializer(PrivacySettings.for_user(request.user)).data)

    @extend_schema(
        tags=["me"],
        request=PrivacyUpdateSerializer,
        responses={200: PrivacySerializer, 400: err("VALIDATION_ERROR")},
    )
    def patch(self, request):
        ser = PrivacyUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = dict(ser.validated_data)
        privacy = PrivacySettings.for_user(request.user)
        mode = data.pop("private_mode", None)
        if mode is not None:
            services.set_private_mode(request.user, mode)
        for field, value in data.items():
            setattr(privacy, field, value)
        if data:
            privacy.save(update_fields=[*data.keys(), "updated_at"])
        if data or mode is not None:
            events.publish_domain("feed.invalidate", {"user_id": str(request.user.pk)})
        return Response(PrivacySerializer(privacy).data)


class ConsentListView(APIView):
    """NFR-PRIV-01: itemised consents with plain-language descriptions."""

    @extend_schema(tags=["me"], responses={200: ConsentItemSerializer(many=True)})
    def get(self, request):
        items = services.consent_summary(request.user)
        return Response(ConsentItemSerializer(items, many=True).data)


class ConsentDetailView(APIView):
    """NFR-PRIV-01: give or withdraw one purpose, as easily as it was given."""

    @extend_schema(
        tags=["me"],
        parameters=[
            OpenApiParameter(
                "purpose", OpenApiTypes.STR, OpenApiParameter.PATH,
                enum=[p.value for p in ConsentPurpose],
            )
        ],
        request=ConsentUpdateSerializer,
        responses={
            200: ConsentItemSerializer,
            404: err("UNKNOWN_PURPOSE"),
            409: err("CONSENT_REQUIRED"),
        },
    )
    def post(self, request, purpose: str):
        if purpose not in ConsentPurpose.values:
            raise ApiError("UNKNOWN_PURPOSE", "Unknown consent purpose.", 404)
        ser = ConsentUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if ser.validated_data["given"]:
            services.give_consent(request.user, purpose)
        else:
            if purpose in REQUIRED_PURPOSES:
                raise ApiError(
                    "CONSENT_REQUIRED",
                    "This is needed to run your account. To stop it, delete your account.",
                    409,
                )
            services.withdraw_consent(request.user, purpose)
        item = next(i for i in services.consent_summary(request.user) if i["purpose"] == purpose)
        return Response(ConsentItemSerializer(item).data)


class ExportView(APIView):
    """JNG-13-04 / NFR-PRIV-06: download my data as JSON."""

    @extend_schema(tags=["me"], responses={200: OpenApiTypes.OBJECT, 429: err("RATE_LIMITED")})
    @ratelimit(key="user", rate="10/h", scope="me.export")
    def get(self, request):
        body = json.dumps(services.export_account(request.user), cls=DjangoJSONEncoder, indent=2)
        resp = HttpResponse(body, content_type="application/json")
        resp["Content-Disposition"] = 'attachment; filename="jingle-export.json"'
        resp["Cache-Control"] = "private, no-store"
        return resp
