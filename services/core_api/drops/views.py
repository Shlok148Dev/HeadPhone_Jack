"""Daily Drop API (JNG-14-01)."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from core_api.idempotency import idempotent
from core_api.ratelimit import ratelimit
from core_api.schema import err
from feed.resolver import _links, _search_links
from social.views import PersonSerializer, person

from . import services
from .models import NOTE_MAX, Drop


class DropSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    user = PersonSerializer()
    title = serializers.CharField()
    artist = serializers.CharField()
    note = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()
    links = serializers.DictField()
    search_links = serializers.DictField()
    artwork_url = serializers.CharField(allow_null=True)
    artwork_small = serializers.CharField(allow_null=True)
    artwork_colors = serializers.DictField(allow_null=True)


class TodaySerializer(serializers.Serializer):
    day = serializers.DateField()
    mine = DropSerializer(allow_null=True)
    streak = serializers.IntegerField()
    locked = serializers.BooleanField()
    friends = DropSerializer(many=True)
    dropped = PersonSerializer(many=True)


def payload(drops: list[Drop], viewer) -> list[dict]:
    from artwork.services import enrich

    rows = [
        {
            "id": d.pk,
            "user": person(d.user, "self" if d.user_id == viewer.pk else "friends"),
            "title": d.title,
            "artist": d.artist,
            "note": d.note,
            "created_at": d.created_at,
            "links": _links(str(d.recording_id) if d.recording_id else None),
            "search_links": _search_links(d.title, d.artist),
        }
        for d in drops
    ]
    return enrich(rows)


class TodayView(APIView):
    """JNG-14-01: today's drop, your streak, and friends' drops (revealed once you've dropped)."""

    @extend_schema(tags=["drops"], responses={200: TodaySerializer})
    def get(self, request):
        me = request.user
        mine = (
            Drop.objects.filter(user=me, day=services.today_for(me)).select_related("user").first()
        )
        friends = services.friends_today(me)
        return Response(
            {
                "day": services.today_for(me),
                "mine": payload([mine], me)[0] if mine else None,
                "streak": services.streak(me),
                "locked": mine is None,
                # Before you drop: who dropped, never what (no titles leak through a locked card).
                "friends": payload(friends, me) if mine else [],
                "dropped": [person(d.user, "friends") for d in friends],
            }
        )


class DropsView(APIView):
    @extend_schema(
        tags=["drops"],
        request=inline_serializer(
            "DropCreate",
            {
                "title": serializers.CharField(max_length=500),
                "artist": serializers.CharField(max_length=500),
                "note": serializers.CharField(
                    max_length=NOTE_MAX, required=False, allow_blank=True
                ),
                "recording_id": serializers.UUIDField(required=False, allow_null=True),
            },
        ),
        responses={201: DropSerializer, 400: err("VALIDATION_ERROR"), 409: err("ALREADY_DROPPED")},
    )
    @ratelimit(key="user", rate="20/d", scope="drops.create")
    @idempotent(required=False)
    def post(self, request):
        d = request.data
        drop = services.create(
            request.user,
            title=str(d.get("title") or ""),
            artist=str(d.get("artist") or ""),
            note=str(d.get("note") or ""),
            recording_id=d.get("recording_id") or None,
        )
        drop = Drop.objects.select_related("user").get(pk=drop.pk)
        return Response(payload([drop], request.user)[0], status=201)
