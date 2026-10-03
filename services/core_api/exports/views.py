"""Exports API (JNG-04-09): play a circle playlist in order in your own app."""

from __future__ import annotations

import re

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from circles.services import require_member
from circles.views import _circle
from core_api.errors import ApiError
from core_api.ratelimit import ratelimit

from . import services
from .models import PLATFORMS, PlaylistExport

_URL_HOSTS = {
    "spotify": ("https://open.spotify.com/",),
    "apple_music": ("https://music.apple.com/",),
    "youtube_music": ("https://music.youtube.com/", "https://www.youtube.com/"),
}
_EXTERNAL_ID = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")


class ExportConfigView(APIView):
    @extend_schema(tags=["exports"], responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return Response(services.config())


class AppleTokenView(APIView):
    """MusicKit developer token for the browser (the user's Music User Token never comes here)."""

    @extend_schema(tags=["exports"], responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT})
    @ratelimit(key="user", rate="30/h", scope="exports.apple.token")
    def get(self, request):
        if not services.apple_enabled():
            raise ApiError("NOT_CONFIGURED", "Apple Music isn't set up on this Jingle yet.", 404)
        return Response({"token": services.apple_developer_token()})


class YouTubeMatchView(APIView):
    """Server-side YouTube matches for a circle's songs (members only; cached per song)."""

    @extend_schema(tags=["exports"], responses={200: OpenApiTypes.OBJECT})
    @ratelimit(key="user", rate="30/h", scope="exports.youtube.match")
    def post(self, request, circle_id):
        c = _circle(circle_id)
        require_member(c, request.user)
        songs = [
            {"key": i.track_key, "title": i.title, "artist": i.artist}
            for i in c.playlist.order_by("added_at")[: services.MAX_MATCH_BATCH]
        ]
        if not services.config()["youtube_music"]["enabled"]:
            raise ApiError("NOT_CONFIGURED", "YouTube Music isn't set up on this Jingle yet.", 404)
        return Response({"matches": services.youtube_matches(songs)})


class PlaylistExportView(APIView):
    """Where this user's copy of the circle playlist lives in each app (update, not duplicate)."""

    @extend_schema(tags=["exports"], responses={200: OpenApiTypes.OBJECT})
    def get(self, request, circle_id):
        c = _circle(circle_id)
        require_member(c, request.user)
        rows = PlaylistExport.objects.filter(user=request.user, circle=c)
        return Response(
            {
                e.platform: {
                    "external_id": e.external_id,
                    "url": e.url,
                    "track_keys": e.track_keys,
                    "updated_at": e.updated_at,
                }
                for e in rows
            }
        )

    @extend_schema(
        tags=["exports"], request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT}
    )
    def put(self, request, circle_id, platform: str):
        c = _circle(circle_id)
        require_member(c, request.user)
        if platform not in PLATFORMS:
            raise ApiError("NOT_FOUND", "Unknown app.", 404)
        d = request.data
        ext, url, keys = (
            str(d.get("external_id") or ""),
            str(d.get("url") or ""),
            d.get("track_keys") or [],
        )
        if not _EXTERNAL_ID.match(ext) or not url.startswith(_URL_HOSTS[platform]):
            raise ApiError(
                "VALIDATION_ERROR", "That doesn't look like a playlist in that app.", 400
            )
        if (
            not isinstance(keys, list)
            or len(keys) > 500
            or not all(isinstance(k, str) and len(k) <= 600 for k in keys)
        ):
            raise ApiError("VALIDATION_ERROR", "track_keys must be a list of songs.", 400)
        PlaylistExport.objects.update_or_create(
            user=request.user,
            circle=c,
            platform=platform,
            defaults={"external_id": ext, "url": url, "track_keys": keys},
        )
        return Response({"ok": True})
