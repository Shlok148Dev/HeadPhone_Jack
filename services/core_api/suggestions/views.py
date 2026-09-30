"""Suggestions API (JNG-03-01, 03-05, 03-06, 03-07; Tech Bible 4.2). Reads precomputed results
(NFR-PERF-08) and re-applies every hard filter at read time, so a block, dismissal, new friend or
discoverability change takes effect before the next nightly run."""

from __future__ import annotations

import json
import logging
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core_api.errors import ApiError
from core_api.redis_client import get_redis
from core_api.schema import err
from social.models import Friendship
from social.services import blocked_ids
from social.views import PersonSerializer, person

from .models import FeedbackAction, SuggestionFeedback, TasteSeed

log = logging.getLogger(__name__)
DISMISS_DAYS = 90
GENRES = (
    "Bollywood",
    "Indie",
    "Hip-hop",
    "Pop",
    "Punjabi",
    "Rock",
    "R&B",
    "Electronic",
    "Indie pop",
    "Sufi",
    "Classical",
    "Jazz",
    "Lo-fi",
    "Metal",
    "K-pop",
    "Tamil",
    "Telugu",
    "Folk",
)


def _schedule(*user_ids) -> None:
    from jingle_ml.tasks import schedule_recompute

    schedule_recompute(*user_ids)


class SuggestionItemSerializer(serializers.Serializer):
    user = PersonSerializer()
    score = serializers.FloatField()
    reasons = serializers.ListField(child=serializers.CharField(), max_length=3)


class SuggestionsResponseSerializer(serializers.Serializer):
    results = SuggestionItemSerializer(many=True)
    pending = serializers.BooleanField()
    cold_start = serializers.BooleanField()


class SuggestionsView(APIView):
    @extend_schema(tags=["suggestions"], responses={200: SuggestionsResponseSerializer})
    def get(self, request):
        me = request.user
        try:
            raw = get_redis().get(f"sug:{me.pk}")
        except Exception:  # noqa: BLE001 - cache down: degrade to empty, never error
            raw = None
        if raw is None:
            _schedule(me.pk)
        items = json.loads(raw) if raw else []
        ids = [i["user_id"] for i in items]
        hidden = {str(x) for x in blocked_ids(me.pk)}
        related = set()
        for lo, hi in Friendship.objects.filter(
            Q(user_low_id=me.pk) | Q(user_high_id=me.pk)
        ).values_list("user_low_id", "user_high_id"):
            related |= {str(lo), str(hi)}
        since = timezone.now() - timedelta(days=DISMISS_DAYS)
        dismissed = {
            str(c)
            for c in SuggestionFeedback.objects.filter(
                user=me, action=FeedbackAction.DISMISSED, at__gte=since
            ).values_list("candidate_id", flat=True)
        }
        users = {
            str(u.pk): u
            for u in User.objects.filter(
                pk__in=ids, is_active=True, deleted_at__isnull=True, discoverable=True
            )
        }
        results = []
        for i in items:
            uid = i["user_id"]
            u = users.get(uid)
            if u is None or uid in hidden or uid in related or uid in dismissed:
                continue
            results.append(
                {"user": person(u, "none"), "score": i["score"], "reasons": i["reasons"][:3]}
            )
        has_friends = bool(related - {str(me.pk)})
        has_seed = TasteSeed.objects.filter(user=me).exists()
        return Response(
            {
                "results": results[:20],
                "pending": raw is None,
                "cold_start": not has_friends and not has_seed and not results,
            }
        )


class DismissView(APIView):
    """JNG-03-05: dismissed people don't return for 90 days."""

    @extend_schema(tags=["suggestions"], request=None, responses={204: None, 404: err("NOT_FOUND")})
    def post(self, request, user_id):
        cand = User.objects.filter(pk=user_id).first()
        if cand is None:
            raise ApiError("NOT_FOUND", "Not found.", 404)
        SuggestionFeedback.objects.create(
            user=request.user, candidate=cand, action=FeedbackAction.DISMISSED
        )
        return Response(status=204)


class TasteView(APIView):
    """JNG-03-07: provisional taste from onboarding (3+ artists or genres)."""

    @extend_schema(
        tags=["suggestions"],
        responses={
            200: inline_serializer(
                "Taste",
                {
                    "artists": serializers.ListField(child=serializers.CharField()),
                    "genres": serializers.ListField(child=serializers.CharField()),
                    "genre_options": serializers.ListField(child=serializers.CharField()),
                },
            )
        },
    )
    def get(self, request):
        seed = TasteSeed.objects.filter(user=request.user).first()
        return Response(
            {
                "artists": seed.artists if seed else [],
                "genres": seed.genres if seed else [],
                "genre_options": list(GENRES),
            }
        )

    @extend_schema(
        tags=["suggestions"],
        request=inline_serializer(
            "TasteUpdate",
            {
                "artists": serializers.ListField(
                    child=serializers.CharField(max_length=80), max_length=20
                ),
                "genres": serializers.ListField(
                    child=serializers.CharField(max_length=40), max_length=20
                ),
            },
        ),
        responses={200: None, 400: err("VALIDATION_ERROR")},
    )
    def put(self, request):
        artists = [str(a).strip()[:80] for a in request.data.get("artists", []) if str(a).strip()][
            :20
        ]
        genres = [g for g in request.data.get("genres", []) if g in GENRES][:20]
        TasteSeed.objects.update_or_create(
            user=request.user, defaults={"artists": artists, "genres": genres}
        )
        _schedule(request.user.pk)
        return Response({"artists": artists, "genres": genres, "genre_options": list(GENRES)})
