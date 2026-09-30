"""Social graph API (EP-02, JNG-12-01; Tech Bible 4.2)."""

from __future__ import annotations

import io

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core_api.errors import ApiError
from core_api.ratelimit import ratelimit
from core_api.schema import err

from . import services
from .models import Friendship, FriendshipStatus, InviteLink, Report, ReportReason


class PersonSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    display_name = serializers.CharField()
    avatar_url = serializers.CharField(allow_null=True)
    relationship = serializers.ChoiceField(
        choices=["self", "friends", "outgoing", "incoming", "none"]
    )


def person(u: User, rel: str) -> dict:
    return {
        "id": u.pk,
        "username": u.username,
        "display_name": u.display_name or u.username,
        "avatar_url": None,
        "relationship": rel,
    }


def _active_user(user_id) -> User:
    u = User.objects.filter(pk=user_id, is_active=True, deleted_at__isnull=True).first()
    if u is None:
        raise ApiError("NOT_FOUND", "We couldn't find that person.", 404)
    return u


class FriendsView(APIView):
    """JNG-02-02: my accepted friends."""

    @extend_schema(tags=["social"], responses={200: PersonSerializer(many=True)})
    def get(self, request):
        ids = services.friend_ids(request.user.pk)
        users = User.objects.filter(pk__in=ids, is_active=True, deleted_at__isnull=True).order_by(
            "display_name"
        )
        return Response(PersonSerializer([person(u, "friends") for u in users], many=True).data)


class FriendDetailView(APIView):
    """JNG-02-03: remove a friend."""

    @extend_schema(tags=["social"], responses={204: None, 404: err("NOT_FOUND")})
    def delete(self, request, user_id):
        services.remove_friend(request.user, user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RequestSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    direction = serializers.ChoiceField(choices=["incoming", "outgoing"])
    user = PersonSerializer()
    created_at = serializers.DateTimeField()


class FriendRequestsView(APIView):
    @extend_schema(tags=["social"], responses={200: RequestSerializer(many=True)})
    def get(self, request):
        me = request.user.pk
        rows = Friendship.objects.filter(
            Q(user_low_id=me) | Q(user_high_id=me), status=FriendshipStatus.PENDING
        )
        hidden = services.blocked_ids(me)
        others = {
            u.pk: u for u in User.objects.filter(pk__in=[r.other(me) for r in rows], is_active=True)
        }
        out = []
        for r in rows.order_by("-created_at"):
            other = others.get(r.other(me))
            if other is None or other.pk in hidden:
                continue
            direction = "outgoing" if str(r.requested_by_id) == str(me) else "incoming"
            out.append(
                {
                    "id": r.pk,
                    "direction": direction,
                    "user": person(other, direction),
                    "created_at": r.created_at,
                }
            )
        return Response(out)

    @extend_schema(
        tags=["social"],
        request=inline_serializer(
            "SendFriendRequest",
            {
                "user_id": serializers.UUIDField(required=False),
                "username": serializers.CharField(required=False),
            },
        ),
        responses={201: PersonSerializer, 404: err("NOT_FOUND"), 429: err("RATE_LIMITED")},
    )
    @ratelimit(key="user", rate="60/h", scope="social.request")
    def post(self, request):
        uid, uname = request.data.get("user_id"), request.data.get("username")
        target = None
        if uid:
            target = User.objects.filter(pk=uid).first()
        elif uname:
            target = User.objects.filter(username__iexact=str(uname).strip().lstrip("@")).first()
        if target is None:
            raise ApiError("NOT_FOUND", "We couldn't find that person.", 404)
        services.send_request(request.user, target)
        return Response(
            person(target, services.relationship(request.user.pk, target.pk)), status=201
        )


class FriendRequestActionView(APIView):
    @extend_schema(
        tags=["social"],
        operation_id="friends_requests_respond",
        request=None,
        responses={200: None, 204: None, 404: err("NOT_FOUND")},
    )
    def post(self, request, request_id, action: str):
        f = Friendship.objects.filter(pk=request_id).first()
        if f is None:
            raise ApiError("NOT_FOUND", "That request isn't there any more.", 404)
        if action == "accept":
            services.accept(request.user, f)
            return Response({"status": "accepted"})
        if action == "decline":
            services.decline(request.user, f)
            return Response(status=204)
        raise ApiError("NOT_FOUND", "Unknown action.", 404)


class FriendRequestCancelView(APIView):
    """Cancel my own pending request."""

    @extend_schema(tags=["social"], responses={204: None, 404: err("NOT_FOUND")})
    def delete(self, request, request_id):
        f = Friendship.objects.filter(pk=request_id).first()
        if f is None:
            raise ApiError("NOT_FOUND", "That request isn't there any more.", 404)
        services.cancel(request.user, f)
        return Response(status=204)


class UserSearchView(APIView):
    """JNG-02-01: by username, or display name if discoverable. Blocks hide both ways."""

    @extend_schema(
        tags=["social"],
        parameters=[OpenApiParameter("q", str)],
        responses={200: PersonSerializer(many=True)},
    )
    @ratelimit(key="user", rate="60/m", scope="social.search")
    def get(self, request):
        q = str(request.GET.get("q", "")).strip().lstrip("@")[:40]
        if len(q) < 2:
            return Response([])
        hidden = services.blocked_ids(request.user.pk) | {request.user.pk}
        qs = (
            User.objects.filter(is_active=True, deleted_at__isnull=True)
            .filter(Q(username__istartswith=q) | Q(discoverable=True, display_name__icontains=q))
            .exclude(pk__in=hidden)
            .order_by("username")[:20]
        )
        return Response([person(u, services.relationship(request.user.pk, u.pk)) for u in qs])


class BlocksView(APIView):
    @extend_schema(tags=["social"], responses={200: PersonSerializer(many=True)})
    def get(self, request):
        users = User.objects.filter(pk__in=request.user.blocks_made.values("blocked_id"))
        return Response([person(u, "none") for u in users])

    @extend_schema(
        tags=["social"],
        request=inline_serializer("BlockUser", {"user_id": serializers.UUIDField()}),
        responses={201: None, 404: err("NOT_FOUND")},
    )
    def post(self, request):
        services.block(request.user, _active_user(request.data.get("user_id")))
        return Response(status=201)


class BlockDetailView(APIView):
    @extend_schema(tags=["social"], responses={204: None})
    def delete(self, request, user_id):
        services.unblock(request.user, user_id)
        return Response(status=204)


class ReportsView(APIView):
    """JNG-12-01: report a user (circles, notes and comments join as they ship)."""

    @extend_schema(
        tags=["social"],
        request=inline_serializer(
            "CreateReport",
            {
                "target_type": serializers.ChoiceField(choices=["user"]),
                "target_id": serializers.UUIDField(),
                "reason": serializers.ChoiceField(choices=ReportReason.choices),
                "details": serializers.CharField(required=False, allow_blank=True, max_length=1000),
            },
        ),
        responses={201: None, 400: err("VALIDATION_ERROR"), 429: err("RATE_LIMITED")},
    )
    @ratelimit(key="user", rate="20/d", scope="social.report")
    def post(self, request):
        reason = request.data.get("reason")
        if reason not in ReportReason.values or request.data.get("target_type", "user") != "user":
            raise ApiError("VALIDATION_ERROR", "Choose a reason.", 400)
        target = _active_user(request.data.get("target_id"))
        Report.objects.create(
            reporter=request.user,
            target_type="user",
            target_id=target.pk,
            reason=reason,
            details=str(request.data.get("details", ""))[:1000],
        )
        return Response(status=201)


def _invite_payload(link: InviteLink) -> dict:
    url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/invite/{link.code}"
    buf = io.BytesIO()
    qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2).save(buf)
    return {"code": link.code, "url": url, "qr_svg": buf.getvalue().decode()}


InviteSerializer = inline_serializer(
    "Invite",
    {
        "code": serializers.CharField(),
        "url": serializers.URLField(),
        "qr_svg": serializers.CharField(),
    },
)


class MyInviteView(APIView):
    """JNG-02-07: my invite link and QR code."""

    @extend_schema(tags=["social"], responses={200: InviteSerializer})
    def get(self, request):
        return Response(_invite_payload(services.invite_for(request.user)))

    @extend_schema(tags=["social"], request=None, responses={200: InviteSerializer})
    def post(self, request):  # rotate: the old link stops working
        return Response(_invite_payload(services.rotate_invite(request.user)))


class InviteView(APIView):
    """Public preview (first name only) and accept, which sends a request to the owner."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["social"],
        auth=[],
        responses={
            200: inline_serializer("InvitePreview", {"display_name": serializers.CharField()}),
            404: err("NOT_FOUND"),
        },
    )
    def get(self, request, code: str):
        link = (
            InviteLink.objects.select_related("owner")
            .filter(code=code[:24], owner__is_active=True)
            .first()
        )
        if link is None:
            raise ApiError("NOT_FOUND", "This invite link doesn't work any more.", 404)
        return Response({"display_name": link.owner.display_name or link.owner.username})

    @extend_schema(
        tags=["social"], request=None, responses={201: PersonSerializer, 404: err("NOT_FOUND")}
    )
    @ratelimit(key="user", rate="30/h", scope="social.invite")
    def post(self, request, code: str):
        if not request.user.is_authenticated:
            raise ApiError("UNAUTHENTICATED", "Sign in to accept this invite.", 401)
        link = InviteLink.objects.select_related("owner").filter(code=code[:24]).first()
        if link is None:
            raise ApiError("NOT_FOUND", "This invite link doesn't work any more.", 404)
        if link.owner_id == request.user.pk:
            return Response(person(link.owner, "self"), status=201)
        services.send_request(request.user, link.owner)
        return Response(
            person(link.owner, services.relationship(request.user.pk, link.owner_id)), status=201
        )
