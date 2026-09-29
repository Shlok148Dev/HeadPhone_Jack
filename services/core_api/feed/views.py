from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsOnboarded
from core_api.schema import err
from sources.models import LinkedSource, PlatformConnection, ScrobbleToken, SourceKind, SourceStatus

from .capabilities import NOTES, capabilities
from .resolver import resolve_card

# ---------------------------------------------------------------- schema-only serializers


class FriendRefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    display_name = serializers.CharField()
    avatar_url = serializers.URLField(allow_null=True)


class LinksSerializer(serializers.Serializer):
    SPOTIFY = serializers.URLField(allow_null=True)
    APPLE_MUSIC = serializers.URLField(allow_null=True)
    AMAZON_MUSIC = serializers.URLField(allow_null=True)
    YOUTUBE_MUSIC = serializers.URLField(allow_null=True)


class CardRecordingSerializer(serializers.Serializer):
    id = serializers.UUIDField(allow_null=True)
    title = serializers.CharField()
    artist = serializers.CharField()
    album = serializers.CharField(allow_null=True)
    artwork_url = serializers.URLField(allow_null=True)
    links = LinksSerializer()


class FeedCardSerializer(serializers.Serializer):
    """CONTRACTS.md §7. Never carries the ingestion route (BR-14)."""

    friend = FriendRefSerializer()
    state = serializers.ChoiceField(choices=["LIVE", "RECENT", "TOP", "HIDDEN"])
    platform = serializers.ChoiceField(
        choices=["SPOTIFY", "APPLE_MUSIC", "AMAZON_MUSIC", "YOUTUBE_MUSIC", "UNKNOWN"],
        allow_null=True,
        help_text="Null when HIDDEN.",
    )
    recording = CardRecordingSerializer(allow_null=True)
    observed_at = serializers.DateTimeField(
        required=False, help_text="Omitted when the owner hides precise time, and for TOP/HIDDEN."
    )
    freshness_label = serializers.CharField()
    degraded = serializers.BooleanField()
    attribution = serializers.ChoiceField(choices=["SPOTIFY"], allow_null=True)


class CapabilitiesSerializer(serializers.Serializer):
    live_on_web = serializers.BooleanField()
    live_on_phone = serializers.BooleanField()
    history = serializers.BooleanField()


class ConnectionSerializer(serializers.Serializer):
    platform = serializers.CharField()
    status = serializers.CharField()
    first_play_at = serializers.DateTimeField(allow_null=True)
    last_signal_at = serializers.DateTimeField(allow_null=True)
    capabilities = CapabilitiesSerializer()
    note = serializers.CharField(allow_blank=True)


# ---------------------------------------------------------------- views


class MyCardView(APIView):
    """JNG-05-01: my own card (Live / Recent / Top) with platform and freshness."""

    permission_classes = [IsAuthenticated, IsOnboarded]

    @extend_schema(
        tags=["feed"],
        responses={200: FeedCardSerializer, 401: err("UNAUTHENTICATED"),
                   403: err("ONBOARDING_REQUIRED")},
    )
    def get(self, request):
        resp = Response(resolve_card(request.user, request.user))
        resp["Cache-Control"] = "private, no-store"
        return resp


class ConnectionsView(APIView):
    """BR-13/BR-15: one row per platform with honest capabilities. No route words (BR-14)."""

    @extend_schema(tags=["sources"], responses={200: ConnectionSerializer(many=True)})
    def get(self, request):
        user = request.user
        rows = list(PlatformConnection.objects.filter(user=user).order_by("created_at"))
        kinds = set(
            LinkedSource.objects.filter(user=user, status=SourceStatus.CONNECTED).values_list(
                "kind", flat=True
            )
        )
        has_companion = SourceKind.COMPANION in kinds or ScrobbleToken.objects.filter(
            user=user, revoked_at__isnull=True
        ).exists()
        data = [
            {
                "platform": c.platform,
                "status": c.status,
                "first_play_at": c.first_play_at,
                "last_signal_at": c.last_signal_at,
                "capabilities": capabilities(c.platform, c.status, kinds, has_companion),
                "note": NOTES.get(c.platform, ""),
            }
            for c in rows
        ]
        return Response(ConnectionSerializer(data, many=True).data)
