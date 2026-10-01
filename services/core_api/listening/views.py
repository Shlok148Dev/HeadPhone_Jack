"""Live sessions API (Tech Bible 4.2 REST fallback: `POST /sessions`, `/sessions/{id}/queue`,
`/queue/{entry}/vote`). The socket carries hints and state; every write happens here."""

from __future__ import annotations

from django.db.models import Q
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from circles.models import CircleMember
from core_api.errors import ApiError
from core_api.ratelimit import ratelimit
from core_api.schema import err
from feed.resolver import _links, _search_links

from . import services
from .models import ListeningSession


class SessionPersonSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    display_name = serializers.CharField()


class ParticipantSerializer(SessionPersonSerializer):
    online = serializers.BooleanField()


class EntrySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    recording_id = serializers.UUIDField(allow_null=True)
    title = serializers.CharField()
    artist = serializers.CharField()
    added_by = SessionPersonSerializer(allow_null=True)
    score = serializers.IntegerField()


class SessionStateSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    host = SessionPersonSerializer()
    ended = serializers.BooleanField()
    now_playing = EntrySerializer(allow_null=True)
    queue = EntrySerializer(many=True)
    participants = ParticipantSerializer(many=True)
    version = serializers.IntegerField()
    my_votes = serializers.DictField(child=serializers.IntegerField())
    joined = serializers.BooleanField()
    now_playing_links = serializers.DictField(allow_null=True)


class SessionSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    host = SessionPersonSerializer()
    circle = serializers.DictField(allow_null=True)
    joined = serializers.BooleanField()
    participant_count = serializers.IntegerField()


def state_for(s: ListeningSession, user) -> dict:
    data = services.public_state(s)
    np = s.now_playing
    data.update(
        version=services.current_version(s),
        my_votes=services.my_votes(s, user),
        joined=s.participants.filter(
            user=user, joined_at__isnull=False, left_at__isnull=True
        ).exists(),
        now_playing_links=(
            {
                "links": _links(str(np.recording_id) if np.recording_id else None),
                "search_links": _search_links(np.title, np.artist),
            }
            if np
            else None
        ),
    )
    return data


class SessionsView(APIView):
    @extend_schema(tags=["sessions"], responses={200: SessionSummarySerializer(many=True)})
    def get(self, request):
        u = request.user
        circles = CircleMember.objects.filter(user=u).values("circle_id")
        rows = (
            ListeningSession.objects.filter(ended_at__isnull=True)
            .filter(Q(participants__user=u) | Q(circle_id__in=circles))
            .select_related("host", "circle")
            .distinct()
            .order_by("-created_at")[:20]
        )
        out = []
        for s in rows:
            if not services.may_join(s, u):
                continue
            active = s.participants.filter(joined_at__isnull=False, left_at__isnull=True)
            out.append(
                {
                    "id": s.pk,
                    "title": s.title,
                    "host": services._person(s.host),
                    "circle": {"id": str(s.circle_id), "name": s.circle.name}
                    if s.circle_id
                    else None,
                    "joined": active.filter(user=u).exists(),
                    "participant_count": active.count(),
                }
            )
        return Response(out)

    @extend_schema(
        tags=["sessions"],
        request=inline_serializer(
            "StartSession",
            {
                "title": serializers.CharField(required=False, allow_blank=True, max_length=80),
                "user_ids": serializers.ListField(child=serializers.UUIDField(), required=False),
                "circle_id": serializers.UUIDField(required=False, allow_null=True),
            },
        ),
        responses={201: SessionStateSerializer, 404: err("NOT_FOUND")},
    )
    @ratelimit(key="user", rate="20/h", scope="sessions.start")
    def post(self, request):
        ids = request.data.get("user_ids") or []
        if not isinstance(ids, list):
            raise ApiError("VALIDATION_ERROR", "user_ids must be a list.", 400)
        s = services.start(
            request.user,
            title=str(request.data.get("title") or ""),
            user_ids=ids,
            circle_id=request.data.get("circle_id") or None,
        )
        return Response(state_for(s, request.user), status=201)


class SessionDetailView(APIView):
    @extend_schema(
        tags=["sessions"], responses={200: SessionStateSerializer, 404: err("NOT_FOUND")}
    )
    def get(self, request, session_id):
        s = services.get_active(session_id)
        if not services.may_join(s, request.user):
            raise ApiError("NOT_FOUND", "This session has ended.", 404)
        return Response(state_for(s, request.user))


class SessionActionView(APIView):
    action = ""

    @extend_schema(
        tags=["sessions"],
        request=None,
        responses={200: SessionStateSerializer, 404: err("NOT_FOUND")},
    )
    def post(self, request, session_id):
        s = services.get_active(session_id)
        if self.action == "join":
            services.join(s, request.user)
        elif self.action == "leave":
            services.leave(s, request.user)
        elif self.action == "next":
            services.next_track(s, request.user)
        elif self.action == "end":
            services.end(s, request.user)
            return Response(state_for(ListeningSession.objects.get(pk=s.pk), request.user))
        return Response(state_for(s, request.user))


def action_view(name: str):
    return type(f"Session{name.title()}View", (SessionActionView,), {"action": name}).as_view()


class QueueView(APIView):
    @extend_schema(
        tags=["sessions"],
        request=inline_serializer(
            "QueueAdd",
            {
                "recording_id": serializers.UUIDField(required=False, allow_null=True),
                "title": serializers.CharField(required=False),
                "artist": serializers.CharField(required=False),
                "anonymous": serializers.BooleanField(required=False),
                "idempotency_key": serializers.CharField(max_length=64),
            },
        ),
        responses={201: EntrySerializer, 400: err("VALIDATION_ERROR"), 404: err("NOT_FOUND")},
    )
    @ratelimit(key="user", rate="60/m", scope="sessions.queue")
    def post(self, request, session_id):
        from moderation.services import require_not_muted

        require_not_muted(request.user)
        s = services.get_active(session_id)
        e = services.add(
            s,
            request.user,
            request.data,
            anonymous=bool(request.data.get("anonymous")),
            key=str(request.data.get("idempotency_key") or ""),
        )
        return Response(services._entry(e), status=201)


class VoteView(APIView):
    @extend_schema(
        tags=["sessions"],
        request=inline_serializer(
            "QueueVote", {"value": serializers.ChoiceField(choices=[1, -1, 0])}
        ),
        responses={200: EntrySerializer, 400: err("VALIDATION_ERROR"), 404: err("NOT_FOUND")},
    )
    @ratelimit(key="user", rate="120/m", scope="sessions.vote")
    def post(self, request, entry_id):
        try:
            value = int(request.data.get("value"))
        except (TypeError, ValueError):
            raise ApiError("VALIDATION_ERROR", "Vote up (1) or down (-1).", 400) from None
        return Response(services._entry(services.vote(entry_id, request.user, value)))
