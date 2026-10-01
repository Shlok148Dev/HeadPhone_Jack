"""Rituals API (EP-09): weekly battles, season table, monthly recap and sharing."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from circles.models import CircleMember, Role
from core_api.errors import ApiError
from core_api.ratelimit import ratelimit
from core_api.schema import err
from feed.resolver import _links, _search_links

from . import services
from .models import VOTES_PER_WEEK, Battle, BattleVote, Recap

BattleSerializer = inline_serializer(
    "Battle",
    {
        "id": serializers.UUIDField(),
        "circle": serializers.DictField(),
        "week": serializers.DateField(),
        "phase": serializers.ChoiceField(
            choices=["upcoming", "nominating", "voting", "closed", "skipped"]
        ),
        "nominate_opens": serializers.DateTimeField(),
        "vote_opens": serializers.DateTimeField(),
        "closes_at": serializers.DateTimeField(),
        "my_nomination": serializers.DictField(allow_null=True),
        "nomination_count": serializers.IntegerField(),
        "nominations": serializers.ListField(child=serializers.DictField()),
        "votes_left": serializers.IntegerField(),
        "results": serializers.ListField(child=serializers.DictField(), allow_null=True),
        "can_skip": serializers.BooleanField(),
    },
)

RecapSerializer = inline_serializer(
    "Recap",
    {
        "id": serializers.UUIDField(),
        "month": serializers.CharField(),
        "data": serializers.DictField(),
        "share_url": serializers.CharField(allow_null=True),
    },
)


def battle_payload(b: Battle, user, member: CircleMember | None = None) -> dict:
    p = services.phase(b)
    mine = b.nominations.filter(user=user).first()
    my_votes = set(
        BattleVote.objects.filter(battle=b, voter=user).values_list("nomination_id", flat=True)
    )
    noms = []
    if p == "voting":
        # Anonymous while voting: judge the song, not the friend (names come with the results).
        for n in b.nominations.order_by("created_at"):
            rid = str(n.recording_id) if n.recording_id else None
            noms.append(
                {
                    "id": str(n.pk),
                    "title": n.title,
                    "artist": n.artist,
                    "recording_id": rid,
                    "mine": n.user_id == user.pk,
                    "my_vote": n.pk in my_votes,
                    "links": _links(rid),
                    "search_links": _search_links(n.title, n.artist),
                }
            )
    return {
        "id": b.pk,
        "circle": {"id": str(b.circle_id), "name": b.circle.name},
        "week": b.week,
        "phase": p,
        "nominate_opens": b.nominate_opens,
        "vote_opens": b.vote_opens,
        "closes_at": b.closes_at,
        "my_nomination": {"title": mine.title, "artist": mine.artist} if mine else None,
        "nomination_count": b.nominations.count(),
        "nominations": noms,
        "votes_left": max(0, VOTES_PER_WEEK - len(my_votes)),
        "results": b.results if p == "closed" else None,
        "can_skip": bool(
            member
            and member.role in (Role.OWNER, Role.ADMIN)
            and p in ("upcoming", "nominating", "voting")
        ),
    }


def recap_payload(r: Recap) -> dict:
    return {
        "id": r.pk,
        "month": r.month,
        "data": r.data,
        "share_url": f"/recap/{r.share_token}" if r.share_token else None,
    }


class RitualsView(APIView):
    @extend_schema(
        tags=["rituals"],
        responses={
            200: inline_serializer(
                "Rituals",
                {"battles": BattleSerializer.__class__(many=True), "recap": RecapSerializer},
            )
        },
    )
    def get(self, request):
        members = (
            CircleMember.objects.filter(user=request.user)
            .select_related("circle")
            .order_by("circle__name")
        )
        battles = [battle_payload(services.battle_for(m.circle), request.user, m) for m in members]
        recap = Recap.objects.filter(user=request.user).order_by("-month").first()
        return Response({"battles": battles, "recap": recap_payload(recap) if recap else None})


class CircleBattleView(APIView):
    @extend_schema(tags=["rituals"], responses={200: BattleSerializer, 404: err("NOT_FOUND")})
    def get(self, request, circle_id):
        circle, m = services.require_member(circle_id, request.user)
        return Response(battle_payload(services.battle_for(circle), request.user, m))


class NominateView(APIView):
    @extend_schema(
        tags=["rituals"],
        request=inline_serializer(
            "Nominate",
            {
                "recording_id": serializers.UUIDField(required=False, allow_null=True),
                "title": serializers.CharField(required=False),
                "artist": serializers.CharField(required=False),
            },
        ),
        responses={200: BattleSerializer, 409: err("NOMINATIONS_CLOSED")},
    )
    @ratelimit(key="user", rate="30/h", scope="battles.nominate")
    def post(self, request, circle_id):
        from moderation.services import require_not_muted

        require_not_muted(request.user)
        circle, m = services.require_member(circle_id, request.user)
        b = services.battle_for(circle)
        services.nominate(b, request.user, request.data)
        return Response(battle_payload(b, request.user, m))


class SkipView(APIView):
    @extend_schema(
        tags=["rituals"], request=None, responses={200: BattleSerializer, 403: err("FORBIDDEN")}
    )
    def post(self, request, circle_id):
        circle, m = services.require_member(circle_id, request.user)
        return Response(battle_payload(services.skip_week(circle, m), request.user, m))


class SeasonView(APIView):
    @extend_schema(
        tags=["rituals"],
        responses={
            200: inline_serializer(
                "Season",
                {
                    "weeks": serializers.IntegerField(),
                    "of": serializers.IntegerField(),
                    "table": serializers.ListField(child=serializers.DictField()),
                },
            )
        },
    )
    def get(self, request, circle_id):
        circle, _ = services.require_member(circle_id, request.user)
        return Response(services.season(circle))


class _BattleAccess(APIView):
    def _battle(self, request, battle_id) -> tuple[Battle, CircleMember]:
        b = Battle.objects.select_related("circle").filter(pk=battle_id).first()
        if b is None:
            raise ApiError("NOT_FOUND", "We couldn't find that battle.", 404)
        _, m = services.require_member(b.circle_id, request.user)
        return b, m


class VoteView(_BattleAccess):
    @extend_schema(
        tags=["rituals"],
        request=inline_serializer("BattleVote", {"nomination_id": serializers.UUIDField()}),
        responses={200: BattleSerializer, 400: err("OWN_NOMINATION"), 409: err("VOTING_CLOSED")},
    )
    @ratelimit(key="user", rate="60/m", scope="battles.vote")
    def post(self, request, battle_id):
        b, m = self._battle(request, battle_id)
        services.vote(b, request.user, request.data.get("nomination_id"))
        return Response(battle_payload(b, request.user, m))


class UnvoteView(_BattleAccess):
    @extend_schema(
        tags=["rituals"], operation_id="battles_unvote", responses={200: BattleSerializer}
    )
    def delete(self, request, battle_id, nomination_id):
        b, m = self._battle(request, battle_id)
        services.unvote(b, request.user, nomination_id)
        return Response(battle_payload(b, request.user, m))


class RecapsView(APIView):
    @extend_schema(tags=["rituals"], responses={200: RecapSerializer.__class__(many=True)})
    def get(self, request):
        return Response(
            [
                recap_payload(r)
                for r in Recap.objects.filter(user=request.user).order_by("-month")[:12]
            ]
        )


class RecapShareView(APIView):
    def _mine(self, request, recap_id) -> Recap:
        r = Recap.objects.filter(pk=recap_id, user=request.user).first()
        if r is None:
            raise ApiError("NOT_FOUND", "We couldn't find that recap.", 404)
        return r

    @extend_schema(
        tags=["rituals"],
        operation_id="recaps_share",
        request=None,
        responses={200: RecapSerializer},
    )
    def post(self, request, recap_id):
        return Response(recap_payload(services.share(self._mine(request, recap_id), True)))

    @extend_schema(
        tags=["rituals"], operation_id="recaps_unshare", responses={200: RecapSerializer}
    )
    def delete(self, request, recap_id):
        return Response(recap_payload(services.share(self._mine(request, recap_id), False)))


class SharedRecapView(APIView):
    """Public, by explicit share only (JNG-09-06). Shows the recap card and a first name."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["rituals"],
        responses={
            200: inline_serializer(
                "SharedRecap",
                {
                    "name": serializers.CharField(),
                    "month": serializers.CharField(),
                    "data": serializers.DictField(),
                },
            ),
            404: err("NOT_FOUND"),
        },
    )
    @ratelimit(key="ip", rate="60/m", scope="recaps.shared")
    def get(self, request, token: str):
        r = Recap.objects.select_related("user").filter(share_token=token[:32]).first()
        if r is None or not r.user.is_active or r.user.deleted_at is not None:
            raise ApiError("NOT_FOUND", "This recap isn't shared any more.", 404)
        name = (r.user.display_name or r.user.username).split(" ")[0]
        return Response({"name": name, "month": r.month, "data": r.data})
