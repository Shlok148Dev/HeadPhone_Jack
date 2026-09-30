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
    search_links = serializers.DictField(child=serializers.URLField(), required=False)


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
        responses={
            200: FeedCardSerializer,
            401: err("UNAUTHENTICATED"),
            403: err("ONBOARDING_REQUIRED"),
        },
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
        has_companion = (
            SourceKind.COMPANION in kinds
            or ScrobbleToken.objects.filter(user=user, revoked_at__isnull=True).exists()
        )
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


# ---- Friends' feed (JNG-05-01, 05-03, 05-06, 05-07) -----------------------------------------

_RANK = {"LIVE": 0, "RECENT": 1, "TOP": 2, "HIDDEN": 3}


def _sort_key(card: dict) -> tuple:
    """BR-02: Live first, then newest Recent, then Top, then Hidden; ties by name."""
    from datetime import datetime

    obs = card.get("observed_at")
    ts = datetime.fromisoformat(obs.replace("Z", "+00:00")).timestamp() if obs else 0.0
    return (_RANK.get(card["state"], 9), -ts, card["friend"]["display_name"].casefold())


class FeedResponseSerializer(serializers.Serializer):
    results = FeedCardSerializer(many=True)
    live_count = serializers.IntegerField()
    degraded = serializers.BooleanField()
    next_cursor = serializers.CharField(allow_null=True)


MAX_FEED = 200  # NFR-PERF-03 sizes the feed for up to 200 friends


def _circle_member_ids(viewer, circle_id: str) -> set:
    import uuid

    from circles.models import CircleMember
    from core_api.errors import ApiError
    from social.services import blocked_ids

    try:
        cid = uuid.UUID(str(circle_id))
    except ValueError:
        raise ApiError("NOT_FOUND", "We couldn't find that circle.", 404) from None
    if not CircleMember.objects.filter(circle_id=cid, user=viewer).exists():
        raise ApiError("NOT_FOUND", "We couldn't find that circle.", 404)
    members = CircleMember.objects.filter(circle_id=cid).exclude(user=viewer)
    return set(members.values_list("user_id", flat=True)) - blocked_ids(viewer.pk)


class FeedView(APIView):
    """Cards of my friends, ordered Live → Recent (newest) → Top → Hidden."""

    permission_classes = [IsAuthenticated, IsOnboarded]

    @extend_schema(tags=["feed"], operation_id="feed_list", responses={200: FeedResponseSerializer})
    def get(self, request):
        from accounts.models import User
        from social.services import friend_ids

        only_live = request.GET.get("filter") == "live"
        ids = friend_ids(request.user.pk)
        circle_id = request.GET.get("circle")
        if circle_id:  # JNG-05-03: scope the feed to one circle I belong to
            ids = _circle_member_ids(request.user, circle_id)
        friends = User.objects.filter(pk__in=ids, is_active=True, deleted_at__isnull=True)[
            :MAX_FEED
        ]
        cards = sorted((resolve_card(f, request.user) for f in friends), key=_sort_key)
        live = sum(1 for c in cards if c["state"] == "LIVE")
        if only_live:
            cards = [c for c in cards if c["state"] == "LIVE"]
        resp = Response(
            {
                "results": cards,
                "live_count": live,
                "degraded": any(c["degraded"] for c in cards),
                "next_cursor": None,
            }
        )
        resp["Cache-Control"] = "private, no-store"
        return resp


class FeedCardDetailView(APIView):
    """One friend's card, fetched after a realtime hint (ADR-0018). Hidden if not visible."""

    permission_classes = [IsAuthenticated, IsOnboarded]

    @extend_schema(tags=["feed"], responses={200: FeedCardSerializer, 404: err("NOT_FOUND")})
    def get(self, request, user_id):
        from accounts.models import User
        from core_api.errors import ApiError
        from core_api.policy import are_friends

        owner = User.objects.filter(pk=user_id, is_active=True, deleted_at__isnull=True).first()
        if owner is None or (owner.pk != request.user.pk and not are_friends(request.user, owner)):
            raise ApiError("NOT_FOUND", "Not found.", 404)
        resp = Response(resolve_card(owner, request.user))
        resp["Cache-Control"] = "private, no-store"
        return resp
