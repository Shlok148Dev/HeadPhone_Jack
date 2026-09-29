"""Auth endpoints under ``/api/v1/auth/`` (JNG-01-01, ADR-0011, NFR-SEC-03/04).

Access token in the JSON body; refresh token only in the HttpOnly cookie ``jingle_refresh``.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth import authenticate
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from core_api.errors import ApiError
from core_api.ratelimit import ratelimit
from core_api.schema import err

from . import services
from .models import User
from .serializers import (
    AuthResponseSerializer,
    GoogleAuthResponseSerializer,
    GoogleSignInSerializer,
    LoginSerializer,
    MeSerializer,
    RegisterSerializer,
)
from .validators import contains_profanity, is_old_enough

log = logging.getLogger(__name__)

def age_restricted() -> ApiError:
    return ApiError(
        "AGE_RESTRICTED", "Jingle is for people aged 18 and over.", status.HTTP_403_FORBIDDEN
    )


def _auth_response(user: User, http_status=status.HTTP_200_OK, **extra) -> Response:
    access, refresh = services.issue_tokens(user)
    body = {"access": access, "user": MeSerializer(user).data, **extra}
    resp = Response(body, status=http_status)
    services.set_refresh_cookie(resp, refresh)
    resp["Cache-Control"] = "no-store"
    return resp


class _PublicAuthView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]


class RegisterView(_PublicAuthView):
    """JNG-01-01: sign up with email. Rejects under-18 birth years (NFR-PRIV-02)."""

    @extend_schema(
        tags=["auth"],
        request=RegisterSerializer,
        responses={
            201: AuthResponseSerializer,
            400: err("VALIDATION_ERROR"),
            403: err("AGE_RESTRICTED"),
            429: err("RATE_LIMITED"),
        },
    )
    @ratelimit(key="ip", rate=settings.AUTH_REGISTER_RATE, scope="auth.register")
    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        if not is_old_enough(data["birth_year"]):
            raise age_restricted()
        user = services.create_account(
            email=data["email"],
            username=data["username"],
            password=data["password"],
            display_name=data.get("display_name") or "",
            birth_year=data["birth_year"],
        )
        return _auth_response(user, status.HTTP_201_CREATED)


class LoginView(_PublicAuthView):
    """JNG-01-01: email + password sign-in."""

    @extend_schema(
        tags=["auth"],
        request=LoginSerializer,
        responses={
            200: AuthResponseSerializer,
            401: err("INVALID_CREDENTIALS"),
            429: err("RATE_LIMITED"),
        },
    )
    @ratelimit(key="ip+email", rate="10/m", scope="auth.login")
    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = authenticate(
            request,
            email=ser.validated_data["email"].strip().lower(),
            password=ser.validated_data["password"],
        )
        if user is None or user.deleted_at is not None:
            raise ApiError("INVALID_CREDENTIALS", "Email or password is incorrect.", 401)
        return _auth_response(user)


class RefreshView(_PublicAuthView):
    """ADR-0011: rotate the refresh cookie; the presented token is blacklisted."""

    @extend_schema(
        tags=["auth"],
        request=None,
        responses={200: AuthResponseSerializer, 401: err("REFRESH_INVALID")},
    )
    @ratelimit(key="ip", rate="30/m", scope="auth.refresh")
    def post(self, request):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not raw:
            raise ApiError("REFRESH_INVALID", "Please sign in again.", 401)
        try:
            token = RefreshToken(raw)
        except TokenError as exc:
            raise ApiError("REFRESH_INVALID", "Please sign in again.", 401) from exc
        user = User.objects.filter(pk=token.payload.get("sub"), is_active=True).first()
        if user is None or user.deleted_at is not None:
            raise ApiError("REFRESH_INVALID", "Please sign in again.", 401)
        token.blacklist()
        return _auth_response(user)


class LogoutView(_PublicAuthView):
    """Blacklist the refresh token and clear the cookie. Always 204."""

    @extend_schema(
        tags=["auth"], request=None, responses={204: OpenApiResponse(description="Signed out")}
    )
    def post(self, request):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass
        resp = Response(status=status.HTTP_204_NO_CONTENT)
        services.clear_refresh_cookie(resp)
        return resp


def verify_google_id_token(token: str) -> dict:
    """Server-side verification with Google's public keys (ADR-0011). Patched in tests."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    return id_token.verify_oauth2_token(
        token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
    )


class GoogleSignInView(_PublicAuthView):
    """JNG-01-01: Google sign-in. First sign-in creates an account that still needs onboarding
    (editable auto-derived username; birth year required before feed access)."""

    @extend_schema(
        tags=["auth"],
        request=GoogleSignInSerializer,
        responses={
            200: GoogleAuthResponseSerializer,
            201: GoogleAuthResponseSerializer,
            401: err("GOOGLE_TOKEN_INVALID"),
            409: err("ACCOUNT_EXISTS"),
            503: err("GOOGLE_SIGNIN_DISABLED"),
        },
    )
    @ratelimit(key="ip", rate="10/m", scope="auth.google")
    def post(self, request):
        if not settings.GOOGLE_OAUTH_CLIENT_ID:
            raise ApiError("GOOGLE_SIGNIN_DISABLED", "Google sign-in is not available.", 503)
        ser = GoogleSignInSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            claims = verify_google_id_token(ser.validated_data["id_token"])
        except ValueError as exc:
            raise ApiError(
                "GOOGLE_TOKEN_INVALID", "Google sign-in failed. Try again.", 401
            ) from exc
        sub = claims.get("sub")
        email = (claims.get("email") or "").strip().lower()
        if not sub or not email or not claims.get("email_verified"):
            raise ApiError("GOOGLE_TOKEN_INVALID", "Google sign-in failed. Try again.", 401)

        user = User.objects.filter(google_sub=sub).first()
        if user is not None:
            if not user.is_active or user.deleted_at is not None:
                raise ApiError("GOOGLE_TOKEN_INVALID", "Google sign-in failed. Try again.", 401)
            return _auth_response(user, created=False)

        if User.objects.filter(email__iexact=email).exists():
            # No silent linking: an unverified email+password account with this address could
            # belong to someone else (account pre-hijacking). The owner signs in with a password.
            raise ApiError(
                "ACCOUNT_EXISTS",
                "An account with this email already exists. Sign in with your password.",
                409,
            )
        name = (claims.get("name") or "").strip()[:60]
        username = services.derive_username(email)
        user = services.create_account(
            email=email,
            username=username,
            password=None,
            display_name="" if contains_profanity(name) else name,
            birth_year=None,
            google_sub=sub,
        )
        return _auth_response(user, status.HTTP_201_CREATED, created=True)
