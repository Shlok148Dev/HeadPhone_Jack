"""Blends API (EP-07: JNG-07-01…04)."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from core_api.errors import ApiError
from core_api.ratelimit import ratelimit
from core_api.schema import err
from feed.resolver import _links, _search_links
from social.views import PersonSerializer, person

from . import services
from .models import Blend, BlendTrack

# JNG-07-04: no platform gives the pilot a write path without approval (Spotify needs an extra
# scope and its allowlist; Apple/Amazon/YouTube have no approved write API here). Say so plainly.
SAVE_NOTE = "Saving to your music app isn't available yet. Open each song, or copy the list."


class BlendTrackSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    recording_id = serializers.UUIDField(allow_null=True)
    title = serializers.CharField()
    artist = serializers.CharField()
    reason = serializers.CharField()
    pinned = serializers.BooleanField()
    links = serializers.DictField(child=serializers.CharField(allow_null=True))
    search_links = serializers.DictField(child=serializers.CharField())


class BlendSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    circle = serializers.DictField(allow_null=True)
    members = PersonSerializer(many=True)
    left_out = PersonSerializer(many=True)
    generated_at = serializers.DateTimeField(allow_null=True)
    track_count = serializers.IntegerField()
    tracks = BlendTrackSerializer(many=True, required=False)
    save = serializers.DictField()


def track_payload(t: BlendTrack) -> dict:
    rid = str(t.recording_id) if t.recording_id else None
    return {
        "id": t.pk,
        "recording_id": rid,
        "title": t.title,
        "artist": t.artist,
        "reason": t.reason,
        "pinned": t.pinned_by_id is not None,
        "links": _links(rid),
        "search_links": _search_links(t.title, t.artist),
    }


def blend_payload(b: Blend, viewer, with_tracks: bool = False) -> dict:
    people = services.members(b)
    allowed = services.contributors(people)
    data = {
        "id": b.pk,
        "name": b.name,
        "circle": {"id": str(b.circle_id), "name": b.circle.name} if b.circle_id else None,
        "members": [person(u, "self" if u.pk == viewer.pk else "friends") for u in people],
        # Members whose plays aren't used because not everyone here may see them (privacy).
        "left_out": [person(u, "friends") for u in people if str(u.pk) not in allowed],
        "generated_at": b.generated_at,
        "track_count": b.tracks.count(),
        "save": {"available": False, "message": SAVE_NOTE},
    }
    if with_tracks:
        data["tracks"] = [track_payload(t) for t in b.tracks.all()]
    return data


class BlendsView(APIView):
    @extend_schema(tags=["blends"], responses={200: BlendSerializer(many=True)})
    def get(self, request):
        rows = Blend.objects.filter(members__user=request.user).select_related("circle")
        return Response([blend_payload(b, request.user) for b in rows.order_by("-created_at")])

    @extend_schema(
        tags=["blends"],
        request=inline_serializer(
            "CreateBlend",
            {
                "user_ids": serializers.ListField(child=serializers.UUIDField(), required=False),
                "circle_id": serializers.UUIDField(required=False, allow_null=True),
                "name": serializers.CharField(required=False, allow_blank=True, max_length=80),
            },
        ),
        responses={201: BlendSerializer, 400: err("VALIDATION_ERROR"), 404: err("NOT_FOUND")},
    )
    @ratelimit(key="user", rate="30/h", scope="blends.create")
    def post(self, request):
        user_ids = request.data.get("user_ids") or []
        if not isinstance(user_ids, list):
            raise ApiError("VALIDATION_ERROR", "user_ids must be a list.", 400)
        b = services.create(
            request.user,
            user_ids=user_ids,
            circle_id=request.data.get("circle_id") or None,
            name=str(request.data.get("name") or "").strip(),
        )
        return Response(blend_payload(b, request.user, with_tracks=True), status=201)


class BlendDetailView(APIView):
    @extend_schema(tags=["blends"], responses={200: BlendSerializer, 404: err("NOT_FOUND")})
    def get(self, request, blend_id):
        b = services.require_member(blend_id, request.user)
        return Response(blend_payload(b, request.user, with_tracks=True))

    @extend_schema(tags=["blends"], responses={204: None, 404: err("NOT_FOUND")})
    def delete(self, request, blend_id):
        services.leave(services.require_member(blend_id, request.user), request.user)
        return Response(status=204)


class RegenerateView(APIView):
    @extend_schema(
        tags=["blends"], request=None, responses={200: BlendSerializer, 404: err("NOT_FOUND")}
    )
    @ratelimit(key="user", rate="30/h", scope="blends.regenerate")
    def post(self, request, blend_id):
        b = services.require_member(blend_id, request.user)
        services.generate(b)
        return Response(blend_payload(b, request.user, with_tracks=True))


class PinView(APIView):
    def _track(self, request, blend_id, track_id) -> BlendTrack:
        b = services.require_member(blend_id, request.user)
        t = b.tracks.filter(pk=track_id).first()
        if t is None:
            raise ApiError("NOT_FOUND", "That song isn't in this Blend.", 404)
        return t

    @extend_schema(
        tags=["blends"],
        operation_id="blends_pin",
        request=None,
        responses={200: BlendTrackSerializer},
    )
    def post(self, request, blend_id, track_id):
        return Response(
            track_payload(
                services.pin(self._track(request, blend_id, track_id), request.user, True)
            )
        )

    @extend_schema(
        tags=["blends"], operation_id="blends_unpin", responses={200: BlendTrackSerializer}
    )
    def delete(self, request, blend_id, track_id):
        return Response(
            track_payload(
                services.pin(self._track(request, blend_id, track_id), request.user, False)
            )
        )
