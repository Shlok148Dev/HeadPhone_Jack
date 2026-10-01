"""Understand API (EP-08): compatibility with its breakdown, my stats, taste timeline, profiles."""

from __future__ import annotations

import json
import logging
from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core_api import policy
from core_api.errors import ApiError
from core_api.ratelimit import ratelimit
from core_api.redis_client import get_redis
from core_api.schema import err
from social.views import PersonSerializer, person

from . import compute

log = logging.getLogger(__name__)
CACHE_S = 6 * 3600
LABELS = {"artists": "Artists", "genres": "Genres", "sound": "Sound"}


class FactorSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    value = serializers.IntegerField()
    weight = serializers.FloatField()
    detail = serializers.CharField()


class CompatibilitySerializer(serializers.Serializer):
    ready = serializers.BooleanField()
    score = serializers.IntegerField(allow_null=True)
    calibrated = serializers.BooleanField()
    breakdown = FactorSerializer(many=True)
    notes = serializers.ListField(child=serializers.CharField())
    shared_artists = serializers.ListField(child=serializers.CharField())
    shared_genres = serializers.ListField(child=serializers.CharField())
    shared_artist_art = serializers.ListField(child=serializers.DictField())
    constellation = serializers.DictField(allow_null=True)
    audio_features_available = serializers.BooleanField()


class NamedCountSerializer(serializers.Serializer):
    name = serializers.CharField()
    plays = serializers.IntegerField()


class NamedShareSerializer(serializers.Serializer):
    name = serializers.CharField()
    share = serializers.FloatField()


class PlatformShareSerializer(serializers.Serializer):
    platform = serializers.CharField()
    share = serializers.FloatField()


class StatsSerializer(serializers.Serializer):
    ready = serializers.BooleanField()
    days_of_data = serializers.IntegerField()
    ready_in_days = serializers.IntegerField()
    plays_30d = serializers.IntegerField(required=False)
    minutes_30d = serializers.IntegerField(required=False)
    top_artists = NamedCountSerializer(many=True, required=False)
    genres = NamedShareSerializer(many=True, required=False)
    platforms = PlatformShareSerializer(many=True, required=False)
    excluded_note = serializers.CharField(allow_null=True, required=False)


class MonthSerializer(serializers.Serializer):
    month = serializers.CharField()
    plays = serializers.IntegerField()
    top_artist = serializers.CharField(allow_null=True)
    genres = NamedShareSerializer(many=True)


def compatibility_payload(me: User, other: User) -> dict:
    key = f"compat:{min(str(me.pk), str(other.pk))}:{max(str(me.pk), str(other.pk))}"
    try:
        cached = get_redis().get(key)
        if cached:
            return json.loads(cached)
    except Exception:  # noqa: BLE001
        cached = None
    since = timezone.now() - timedelta(days=compute.WINDOW_DAYS)
    cu, nu = compute.artist_plays(str(me.pk), since)
    cv, nv = compute.artist_plays(str(other.pk), since)
    tags = compute.genre_tags(set(cu) | set(cv))
    c = compute.compatibility(cu, cv, {**nu, **nv}, tags)
    notes = [compute.SOUND_UNAVAILABLE]
    if not c.ready:
        body = {
            "shared_artist_art": [],
            "constellation": None,
            "ready": False,
            "score": None,
            "calibrated": False,
            "breakdown": [],
            "notes": [
                "Not enough listening yet. Scores appear after a couple of weeks of plays.",
                *notes,
            ],
            "shared_artists": [],
            "shared_genres": [],
            "audio_features_available": False,
        }
    else:
        score, calibrated = compute.percentile(c.raw, compute.load_dist())
        details = {
            "artists": f"{len(c.shared_artists or [])} shared in your top artists"
            if c.shared_artists
            else "No top artists in common yet",
            "genres": ", ".join(c.shared_genres or []) or "Different genres",
        }
        if not c.genres_available:
            notes.insert(0, "Genre comparison unavailable")
        from artwork.services import enrich_artists

        body = {
            "shared_artist_art": enrich_artists(
                [{"name": a} for a in (c.shared_artists or [])[:8]]
            ),
            # Taste Constellation: each person's top artists, shared ones in the overlap.
            "constellation": {
                "mine": enrich_artists(
                    [{"name": {**nu, **nv}.get(a, a)} for a, _ in cu.most_common(7)]
                ),
                "theirs": enrich_artists(
                    [{"name": {**nu, **nv}.get(a, a)} for a, _ in cv.most_common(7)]
                ),
            },
            "ready": True,
            "score": score,
            "calibrated": calibrated,
            "breakdown": [
                {
                    "key": k,
                    "label": LABELS[k],
                    "value": round(100 * v["value"]),
                    "weight": v["weight"],
                    "detail": details[k],
                }
                for k, v in (c.components or {}).items()
            ],
            "notes": notes,
            "shared_artists": c.shared_artists or [],
            "shared_genres": c.shared_genres or [],
            "audio_features_available": False,
        }
    try:
        get_redis().set(key, json.dumps(body), ex=CACHE_S)
    except Exception:  # noqa: BLE001 - cache is best effort
        log.warning("compatibility cache unavailable")
    return body


class CompatibilityView(APIView):
    @extend_schema(
        tags=["insights"], responses={200: CompatibilitySerializer, 404: err("NOT_FOUND")}
    )
    @ratelimit(key="user", rate="60/m", scope="insights.compat")
    def get(self, request, user_id):
        other = User.objects.filter(pk=user_id, is_active=True, deleted_at__isnull=True).first()
        # BR-06/07: only for a friend whose listening I may see.
        if (
            other is None
            or other.pk == request.user.pk
            or not policy.are_friends(request.user, other)
            or not policy.can_view_activity(request.user, other)
        ):
            raise ApiError("NOT_FOUND", "Compatibility isn't available for this person.", 404)
        return Response(compatibility_payload(request.user, other))


class MyStatsView(APIView):
    @extend_schema(tags=["insights"], responses={200: StatsSerializer})
    def get(self, request):
        from artwork.services import enrich_artists

        stats = compute.my_stats(str(request.user.pk))
        if stats.get("top_artists"):
            stats["top_artists"] = enrich_artists(stats["top_artists"])
        return Response(stats)


class MyTimelineView(APIView):
    @extend_schema(tags=["insights"], responses={200: MonthSerializer(many=True)})
    def get(self, request):
        return Response(compute.timeline(str(request.user.pk)))


class ProfileView(APIView):
    @extend_schema(
        tags=["insights"],
        responses={
            200: inline_serializer(
                "Profile",
                {
                    "person": PersonSerializer(),
                    "is_me": serializers.BooleanField(),
                    "compatibility_available": serializers.BooleanField(),
                    "college": serializers.CharField(allow_blank=True),
                    "city": serializers.CharField(allow_blank=True),
                },
            ),
            404: err("NOT_FOUND"),
        },
    )
    def get(self, request, username: str):
        from social.services import relationship

        u = User.objects.filter(
            username__iexact=username[:40], is_active=True, deleted_at__isnull=True
        ).first()
        if u is None or policy.is_blocked_either_way(request.user, u):
            raise ApiError("NOT_FOUND", "We couldn't find that person.", 404)
        me = u.pk == request.user.pk
        rel = "self" if me else relationship(request.user.pk, u.pk)
        friends = rel == "friends"
        return Response(
            {
                "person": person(u, rel),
                "is_me": me,
                "compatibility_available": friends and policy.can_view_activity(request.user, u),
                # Profile fields are shown only to friends (or me): they're opt-in and personal.
                "college": u.college if (me or friends) else "",
                "city": u.city if (me or friends) else "",
            }
        )
