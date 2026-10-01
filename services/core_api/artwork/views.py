"""Artwork API (GET /api/v1/artwork, public wall for the landing page)."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core_api.ratelimit import ratelimit

from . import services
from .models import Artwork, Kind

ArtworkSerializer = inline_serializer(
    "ArtworkResult",
    {
        "found": serializers.BooleanField(),
        "url": serializers.CharField(allow_null=True),
        "url_small": serializers.CharField(allow_null=True),
        "colors": serializers.DictField(),
        "source": serializers.CharField(allow_null=True),
    },
)


class ArtworkView(APIView):
    @extend_schema(
        tags=["artwork"],
        parameters=[OpenApiParameter("title", str), OpenApiParameter("artist", str, required=True)],
        responses={200: ArtworkSerializer},
    )
    @ratelimit(key="user", rate="120/m", scope="artwork.lookup")
    def get(self, request):
        title = str(request.query_params.get("title") or "")[:300]
        artist = str(request.query_params.get("artist") or "")[:300]
        p = (
            services.lookup_track(title, artist)
            if title
            else services.lookup_artists([artist]).get(services.artist_key(artist))
        )
        return Response(
            {
                "found": bool(p),
                "url": p and p["url"],
                "url_small": p and p["url_small"],
                "colors": (p or {}).get("colors", {}),
                "source": p and p["source"],
            }
        )


class ArtworkWallView(APIView):
    """Real covers for the logged-out homepage (public; covers only, no people)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["artwork"],
        responses={
            200: inline_serializer(
                "ArtworkWall", {"covers": serializers.ListField(child=serializers.DictField())}
            )
        },
    )
    @ratelimit(key="ip", rate="60/m", scope="artwork.wall")
    def get(self, request):
        rows = Artwork.objects.filter(kind=Kind.TRACK, status="found", source="itunes").order_by(
            "id"
        )[:60]
        return Response(
            {
                "covers": [
                    {
                        "url": a.url,
                        "url_small": a.url_small,
                        "color": a.colors.get("dominant"),
                        "label": a.key.split("|")[1].title() if "|" in a.key else "",
                    }
                    for a in rows
                ]
            }
        )
