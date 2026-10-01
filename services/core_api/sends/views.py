"""Sends, mixtapes and the inbox (EP-06; Tech Bible 4.2 `POST /recommendations`, `GET /inbox`)."""

from __future__ import annotations

from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from core_api.errors import ApiError
from core_api.ratelimit import ratelimit
from core_api.schema import err
from feed.resolver import _links, _search_links
from social.services import blocked_ids
from social.views import PersonSerializer, person

from . import services
from .models import NOTE_MAX, REACTIONS, Delivery, Kind, Recommendation

STATUSES = ["sent", "delivered", "viewed", "played"]


class SongSerializer(serializers.Serializer):
    recording_id = serializers.UUIDField(allow_null=True)
    title = serializers.CharField()
    artist = serializers.CharField()
    links = serializers.DictField(child=serializers.CharField(allow_null=True))
    search_links = serializers.DictField(child=serializers.CharField())


class ReceivedSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=Kind.choices)
    sender = PersonSerializer()
    note = serializers.CharField()
    items = SongSerializer(many=True)
    circle = serializers.DictField(allow_null=True)
    sent_at = serializers.DateTimeField()
    status = serializers.ChoiceField(choices=STATUSES)
    reaction = serializers.CharField()
    is_reply = serializers.BooleanField()


class RecipientStatusSerializer(serializers.Serializer):
    user = PersonSerializer()
    status = serializers.ChoiceField(choices=STATUSES)
    reaction = serializers.CharField()
    credit_artist = serializers.CharField(allow_null=True)


class SentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=Kind.choices)
    note = serializers.CharField()
    items = SongSerializer(many=True)
    sent_at = serializers.DateTimeField()
    recipients = RecipientStatusSerializer(many=True)


class ItemInSerializer(serializers.Serializer):
    recording_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(required=False, max_length=500)
    artist = serializers.CharField(required=False, max_length=500)


def song(it) -> dict:
    rid = str(it.recording_id) if it.recording_id else None
    return {
        "recording_id": rid,
        "title": it.title,
        "artist": it.artist,
        "links": _links(rid),
        "search_links": _search_links(it.title, it.artist),
    }


def received_payload(d: Delivery) -> dict:
    rec = d.rec
    return {
        "id": d.pk,
        "kind": rec.kind,
        "sender": person(rec.sender, "friends"),
        "note": rec.note,
        "items": [song(it) for it in rec.items.all()],
        "circle": {"id": str(d.circle_id), "name": d.circle.name}
        if d.circle_id and d.circle
        else None,
        "sent_at": rec.created_at,
        "status": d.status,
        "reaction": d.reaction,
        "is_reply": rec.reply_to_id is not None,
    }


def _uuid_list(value, field: str) -> list[str]:
    import uuid

    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ApiError("VALIDATION_ERROR", f"{field} must be a list.", 400)
    try:
        return [str(uuid.UUID(str(v))) for v in value]
    except ValueError:
        raise ApiError("VALIDATION_ERROR", f"{field} has an invalid id.", 400) from None


class RecommendationsView(APIView):
    @extend_schema(
        tags=["sends"],
        operation_id="recommendations_create",
        request=inline_serializer(
            "CreateRecommendation",
            {
                "items": ItemInSerializer(many=True),
                "note": serializers.CharField(
                    required=False, allow_blank=True, max_length=NOTE_MAX
                ),
                "user_ids": serializers.ListField(child=serializers.UUIDField(), required=False),
                "circle_ids": serializers.ListField(child=serializers.UUIDField(), required=False),
                "reply_to": serializers.UUIDField(required=False, allow_null=True),
            },
        ),
        responses={
            201: inline_serializer(
                "CreatedRecommendation",
                {"id": serializers.UUIDField(), "recipients": serializers.IntegerField()},
            ),
            400: err("VALIDATION_ERROR"),
            404: err("NOT_FOUND"),
        },
    )
    @ratelimit(key="user", rate="200/d", scope="sends.create")
    def post(self, request):
        from moderation.services import require_not_muted

        require_not_muted(request.user)
        data = request.data
        items = data.get("items")
        if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
            raise ApiError("VALIDATION_ERROR", "Add a song to send.", 400)
        reply = None
        if data.get("reply_to"):
            reply = services.received(request.user, _uuid_list([data["reply_to"]], "reply_to")[0])
        rec = services.send(
            request.user,
            items,
            note=str(data.get("note") or ""),
            user_ids=_uuid_list(data.get("user_ids"), "user_ids"),
            circle_ids=_uuid_list(data.get("circle_ids"), "circle_ids"),
            reply_to=reply,
        )
        return Response({"id": rec.pk, "recipients": rec.deliveries.count()}, status=201)


class InboxView(APIView):
    @extend_schema(tags=["sends"], responses={200: ReceivedSerializer(many=True)})
    def get(self, request):
        services.mark_delivered(request.user)
        blocked = blocked_ids(request.user.pk)
        rows = (
            Delivery.objects.select_related("rec", "rec__sender", "circle")
            .prefetch_related("rec__items")
            .filter(recipient=request.user)
            .exclude(rec__sender_id__in=blocked)
            .order_by("-rec__created_at")[:100]
        )
        return Response([received_payload(d) for d in rows])


class SentView(APIView):
    @extend_schema(tags=["sends"], responses={200: SentSerializer(many=True)})
    def get(self, request):
        blocked = blocked_ids(request.user.pk)
        recs = (
            Recommendation.objects.filter(sender=request.user)
            .prefetch_related("items", "deliveries__recipient")
            .order_by("-created_at")[:100]
        )
        out = []
        for r in recs:
            out.append(
                {
                    "id": r.pk,
                    "kind": r.kind,
                    "note": r.note,
                    "items": [song(it) for it in r.items.all()],
                    "sent_at": r.created_at,
                    "recipients": [
                        {
                            "user": person(d.recipient, "friends"),
                            "status": d.status,
                            "reaction": d.reaction,
                            "credit_artist": d.credit_artist or None,
                        }
                        for d in r.deliveries.all()
                        if d.recipient_id not in blocked
                    ],
                }
            )
        return Response(out)


class UnreadView(APIView):
    @extend_schema(
        tags=["sends"],
        responses={200: inline_serializer("InboxUnread", {"count": serializers.IntegerField()})},
    )
    def get(self, request):
        services.mark_delivered(request.user)
        n = (
            Delivery.objects.filter(recipient=request.user, viewed_at__isnull=True)
            .exclude(rec__sender_id__in=blocked_ids(request.user.pk))
            .count()
        )
        return Response({"count": n})


class DeliveryActionView(APIView):
    action = "view"

    @extend_schema(
        tags=["sends"],
        request=inline_serializer(
            "React", {"reaction": serializers.ChoiceField(choices=[*REACTIONS, ""], required=False)}
        ),
        responses={200: ReceivedSerializer, 400: err("VALIDATION_ERROR"), 404: err("NOT_FOUND")},
    )
    def post(self, request, delivery_id):
        d = services.received(request.user, delivery_id)
        if self.action == "react":
            d = services.react(d, str(request.data.get("reaction") or ""))
        else:
            d = services.view(d)
        return Response(received_payload(d))


class InboxViewView(DeliveryActionView):
    action = "view"


class InboxReactView(DeliveryActionView):
    action = "react"


class SongSearchView(APIView):
    """Songs already known to Jingle (anyone's resolved plays); no third-party search call."""

    @extend_schema(
        tags=["sends"],
        parameters=[OpenApiParameter("q", str, required=True)],
        responses={200: SongSerializer(many=True)},
    )
    @ratelimit(key="user", rate="60/m", scope="songs.search")
    def get(self, request):
        from sources.models import Recording

        q = str(request.query_params.get("q") or "").strip()[:100]
        if len(q) < 2:
            return Response([])
        words = q.split()[:4]
        qs = Recording.objects.all()
        for w in words:
            qs = qs.filter(Q(title__icontains=w) | Q(artist_name__icontains=w))
        rows = qs.order_by("title")[:20]
        return Response(
            [
                {
                    "recording_id": str(r.pk),
                    "title": r.title,
                    "artist": r.artist_name,
                    "links": _links(str(r.pk)),
                    "search_links": _search_links(r.title, r.artist_name),
                }
                for r in rows
            ]
        )
