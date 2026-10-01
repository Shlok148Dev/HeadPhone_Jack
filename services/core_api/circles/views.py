"""Circles API (EP-04; Tech Bible 4.2)."""

from __future__ import annotations

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.validators import validate_clean_text
from core_api.errors import ApiError
from core_api.ratelimit import ratelimit
from core_api.schema import err
from feed.resolver import resolve_card
from feed.views import FeedCardSerializer, _sort_key
from social.services import blocked_ids
from social.views import PersonSerializer, person

from . import services
from .models import Circle, CircleInvite, CircleMember, Role, SuggestedCircle, Visibility


def _circle(circle_id) -> Circle:
    c = Circle.objects.filter(pk=circle_id).first()
    if c is None:
        raise ApiError("NOT_FOUND", "We couldn't find that circle.", 404)
    return c


def _clean_name(value, user=None) -> str:
    if user is not None:
        from moderation.services import require_not_muted

        require_not_muted(user)
    name = str(value or "").strip()
    if not 1 <= len(name) <= 60:
        raise ApiError("VALIDATION_ERROR", "Give your circle a name (up to 60 characters).", 400)
    try:
        validate_clean_text(name)
    except Exception:  # noqa: BLE001 - profanity filter (JNG-12-07)
        raise ApiError("VALIDATION_ERROR", "Please choose a different name.", 400) from None
    return name


class MemberSerializer(serializers.Serializer):
    user = PersonSerializer()
    role = serializers.ChoiceField(choices=Role.choices)


class CircleSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    visibility = serializers.ChoiceField(choices=Visibility.choices)
    member_count = serializers.IntegerField()
    my_role = serializers.ChoiceField(choices=Role.choices)
    members_can_invite = serializers.BooleanField()
    battle_schedule = serializers.DictField()
    members = MemberSerializer(many=True, required=False)
    covers = serializers.ListField(child=serializers.CharField(), required=False)


def circle_payload(c: Circle, viewer, with_members: bool = False) -> dict:
    mine = services.membership(c, viewer)
    data = {
        "id": c.pk,
        "name": c.name,
        "visibility": c.visibility,
        "member_count": c.member_count,
        "my_role": mine.role if mine else None,
        "members_can_invite": c.members_can_invite,
        "battle_schedule": c.battle_schedule,
    }
    if with_members:
        hidden = blocked_ids(viewer.pk)  # BR-07: blocked people vanish from circles too
        rows = c.members.select_related("user").exclude(user_id__in=hidden).order_by("joined_at")
        data["members"] = [
            {"user": person(m.user, "self" if m.user_id == viewer.pk else "none"), "role": m.role}
            for m in rows
        ]
    return data


def _covers(c: Circle, viewer, limit: int = 4) -> list[str]:
    """Up to four real covers of what members played, each through the viewer's privacy view
    of that member (resolve_card), so a circle tile never reveals more than the feed would."""
    hidden = blocked_ids(viewer.pk)
    users = (
        User.objects.filter(circle_memberships__circle=c, is_active=True, deleted_at__isnull=True)
        .exclude(pk__in=hidden | {viewer.pk})
        .order_by("circle_memberships__joined_at")[:8]
    )
    out: list[str] = []
    for u in users:
        card = resolve_card(u, viewer)
        rec = card.get("recording") if card.get("state") != "HIDDEN" else None
        url = rec and (rec.get("artwork_small") or rec.get("artwork_url"))
        if url and url not in out:
            out.append(url)
        if len(out) == limit:
            break
    return out


class CirclesView(APIView):
    @extend_schema(tags=["circles"], responses={200: CircleSerializer(many=True)})
    def get(self, request):
        ids = CircleMember.objects.filter(user=request.user).values("circle_id")
        circles = Circle.objects.filter(pk__in=ids).order_by("name")
        return Response(
            [
                {**circle_payload(c, request.user), "covers": _covers(c, request.user)}
                for c in circles
            ]
        )

    @extend_schema(
        tags=["circles"],
        request=inline_serializer(
            "CreateCircle",
            {
                "name": serializers.CharField(max_length=60),
                "visibility": serializers.ChoiceField(choices=Visibility.choices, required=False),
            },
        ),
        responses={201: CircleSerializer, 400: err("VALIDATION_ERROR"), 409: err("CIRCLE_LIMIT")},
    )
    @ratelimit(key="user", rate="20/h", scope="circles.create")
    def post(self, request):
        vis = request.data.get("visibility", Visibility.PRIVATE)
        if vis not in Visibility.values:
            raise ApiError("VALIDATION_ERROR", "Choose private or discoverable.", 400)
        c = services.create_circle(
            request.user, _clean_name(request.data.get("name"), request.user), vis
        )
        return Response(circle_payload(c, request.user, with_members=True), status=201)


class CircleDetailView(APIView):
    @extend_schema(tags=["circles"], responses={200: CircleSerializer, 404: err("NOT_FOUND")})
    def get(self, request, circle_id):
        c = _circle(circle_id)
        services.require_member(c, request.user)
        return Response(circle_payload(c, request.user, with_members=True))

    @extend_schema(
        tags=["circles"],
        request=inline_serializer(
            "UpdateCircle",
            {
                "name": serializers.CharField(required=False),
                "visibility": serializers.CharField(required=False),
                "members_can_invite": serializers.BooleanField(required=False),
                "battle_schedule": serializers.DictField(required=False),
            },
        ),
        responses={200: CircleSerializer, 403: err("FORBIDDEN")},
    )
    def patch(self, request, circle_id):
        """JNG-04-07: admins set the name, visibility, who can invite and the battle schedule."""
        c = _circle(circle_id)
        services.require_admin(c, request.user)
        d = request.data
        if "name" in d:
            c.name = _clean_name(d["name"], request.user)
        if "visibility" in d:
            if d["visibility"] not in Visibility.values:
                raise ApiError("VALIDATION_ERROR", "Choose private or discoverable.", 400)
            c.visibility = d["visibility"]
        if "members_can_invite" in d:
            c.members_can_invite = bool(d["members_can_invite"])
        if isinstance(d.get("battle_schedule"), dict):
            allowed = {"nominate", "vote", "close", "skip_week"}
            c.battle_schedule = {
                **c.battle_schedule,
                **{k: v for k, v in d["battle_schedule"].items() if k in allowed},
            }
        c.save()
        return Response(circle_payload(c, request.user, with_members=True))

    @extend_schema(tags=["circles"], responses={204: None})
    def delete(self, request, circle_id):
        """Leave (owners of a one-person circle close it; otherwise they transfer first)."""
        services.leave(_circle(circle_id), request.user)
        return Response(status=204)


class CircleFeedView(APIView):
    """JNG-04-04: members' cards, each under that member's own privacy rules."""

    @extend_schema(tags=["circles"], responses={200: FeedCardSerializer(many=True)})
    def get(self, request, circle_id):
        c = _circle(circle_id)
        services.require_member(c, request.user)
        hidden = blocked_ids(request.user.pk)
        users = User.objects.filter(
            circle_memberships__circle=c, is_active=True, deleted_at__isnull=True
        ).exclude(pk__in=hidden | {request.user.pk})
        return Response(sorted((resolve_card(u, request.user) for u in users), key=_sort_key))


class MemberView(APIView):
    @extend_schema(
        tags=["circles"],
        request=inline_serializer("SetRole", {"role": serializers.CharField()}),
        responses={200: None, 403: err("FORBIDDEN")},
    )
    def patch(self, request, circle_id, user_id):
        m = services.set_role(
            _circle(circle_id), request.user, user_id, str(request.data.get("role", ""))
        )
        return Response({"role": m.role})

    @extend_schema(tags=["circles"], responses={204: None, 403: err("FORBIDDEN")})
    def delete(self, request, circle_id, user_id):
        services.remove_member(_circle(circle_id), request.user, user_id)
        return Response(status=204)


class TransferView(APIView):
    @extend_schema(
        tags=["circles"],
        request=inline_serializer("Transfer", {"user_id": serializers.UUIDField()}),
        responses={204: None},
    )
    def post(self, request, circle_id):
        services.transfer(_circle(circle_id), request.user, request.data.get("user_id"))
        return Response(status=204)


class CircleInvitesView(APIView):
    """Invite friends (direct) — they must accept (BR-08)."""

    @extend_schema(
        operation_id="circles_invite_friends",
        tags=["circles"],
        request=inline_serializer(
            "InviteFriends",
            {"user_ids": serializers.ListField(child=serializers.UUIDField(), max_length=49)},
        ),
        responses={
            201: inline_serializer("Invited", {"invited": serializers.IntegerField()}),
            409: err("CIRCLE_FULL"),
        },
    )
    @ratelimit(key="user", rate="200/d", scope="circles.invite")
    def post(self, request, circle_id):
        c = _circle(circle_id)
        count = 0
        for uid in request.data.get("user_ids", [])[:49]:
            u = User.objects.filter(pk=uid, is_active=True).first()
            if u is not None:
                services.invite_friend(c, request.user, u)
                count += 1
        return Response({"invited": count}, status=201)


class CircleLinkView(APIView):
    @extend_schema(
        tags=["circles"],
        request=None,
        responses={
            201: inline_serializer(
                "CircleLink",
                {"url": serializers.URLField(), "expires_at": serializers.DateTimeField()},
            )
        },
    )
    def post(self, request, circle_id):
        token, inv = services.create_link(_circle(circle_id), request.user)
        url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/circles/join/{token}"
        return Response({"url": url, "expires_at": inv.expires_at}, status=201)


class JoinView(APIView):
    """Share-link landing: public preview, and join for signed-in people."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["circles"],
        auth=[],
        responses={
            200: inline_serializer(
                "CirclePreview",
                {
                    "name": serializers.CharField(),
                    "member_count": serializers.IntegerField(),
                    "full": serializers.BooleanField(),
                },
            ),
            404: err("NOT_FOUND"),
        },
    )
    def get(self, request, token: str):
        c = services.link_invite(token).circle
        return Response(
            {"name": c.name, "member_count": c.member_count, "full": c.member_count >= 50}
        )

    @extend_schema(
        tags=["circles"], request=None, responses={201: CircleSerializer, 409: err("CIRCLE_FULL")}
    )
    def post(self, request, token: str):
        if not request.user.is_authenticated:
            raise ApiError("UNAUTHENTICATED", "Sign in to join this circle.", 401)
        m = services.join_by_link(token, request.user)
        return Response(circle_payload(m.circle, request.user), status=201)


class MyInvitesView(APIView):
    @extend_schema(
        tags=["circles"],
        responses={
            200: inline_serializer(
                "CircleInviteItem",
                {
                    "id": serializers.UUIDField(),
                    "circle": serializers.DictField(),
                    "from": PersonSerializer(),
                },
                many=True,
            )
        },
    )
    def get(self, request):
        rows = CircleInvite.objects.select_related("circle", "created_by").filter(
            invitee=request.user, uses=0, revoked=False, expires_at__gt=timezone.now()
        )
        hidden = blocked_ids(request.user.pk)
        return Response(
            [
                {
                    "id": i.pk,
                    "circle": {
                        "id": str(i.circle_id),
                        "name": i.circle.name,
                        "member_count": i.circle.member_count,
                    },
                    "from": person(i.created_by, "none"),
                }
                for i in rows
                if i.created_by_id not in hidden
            ]
        )


class MyInviteActionView(APIView):
    @extend_schema(
        tags=["circles"], request=None, responses={200: None, 204: None, 404: err("NOT_FOUND")}
    )
    def post(self, request, invite_id, action: str):
        inv = CircleInvite.objects.select_related("circle").filter(pk=invite_id).first()
        if inv is None:
            raise ApiError("NOT_FOUND", "This invite doesn't work any more.", 404)
        if action == "accept":
            m = services.accept_invite(inv, request.user)
            return Response(circle_payload(m.circle, request.user))
        if action == "decline":
            services.decline_invite(inv, request.user)
            return Response(status=204)
        raise ApiError("NOT_FOUND", "Unknown action.", 404)


class SuggestedCirclesView(APIView):
    """JNG-04-05: suggestions only; creating one sends invites, it never adds anyone (BR-08)."""

    @extend_schema(
        tags=["circles"],
        responses={
            200: inline_serializer(
                "SuggestedCircle",
                {
                    "id": serializers.UUIDField(),
                    "name": serializers.CharField(),
                    "members": PersonSerializer(many=True),
                },
                many=True,
            )
        },
    )
    def get(self, request):
        hidden = blocked_ids(request.user.pk)
        out = []
        for s in SuggestedCircle.objects.filter(for_user=request.user, status="pending").order_by(
            "-created_at"
        )[:3]:
            users = User.objects.filter(pk__in=s.member_ids, is_active=True).exclude(
                pk__in=hidden | {request.user.pk}
            )
            out.append(
                {"id": s.pk, "name": s.name, "members": [person(u, "friends") for u in users]}
            )
        return Response(out)


class SuggestedCircleActionView(APIView):
    @extend_schema(
        tags=["circles"],
        request=inline_serializer(
            "UseSuggestion",
            {
                "name": serializers.CharField(required=False),
                "user_ids": serializers.ListField(child=serializers.UUIDField(), required=False),
            },
        ),
        responses={201: CircleSerializer, 204: None},
    )
    def post(self, request, suggestion_id, action: str):
        s = SuggestedCircle.objects.filter(
            pk=suggestion_id, for_user=request.user, status="pending"
        ).first()
        if s is None:
            raise ApiError("NOT_FOUND", "That suggestion isn't there any more.", 404)
        if action == "dismiss":
            s.status = "dismissed"
            s.save(update_fields=["status"])
            return Response(status=204)
        if action != "create":
            raise ApiError("NOT_FOUND", "Unknown action.", 404)
        chosen = [
            str(u)
            for u in request.data.get("user_ids", s.member_ids)
            if str(u) in {str(x) for x in s.member_ids}
        ]
        c = services.create_circle(request.user, _clean_name(request.data.get("name") or s.name))
        for uid in chosen:
            u = User.objects.filter(pk=uid, is_active=True).first()
            if u is not None and u.pk != request.user.pk:
                try:
                    services.invite_friend(c, request.user, u)
                except ApiError:
                    continue
        s.status = "used"
        s.save(update_fields=["status"])
        return Response(circle_payload(c, request.user, with_members=True), status=201)
