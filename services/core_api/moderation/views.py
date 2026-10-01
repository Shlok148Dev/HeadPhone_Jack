"""Staff console API (EP-12) and the member's own moderation status + appeals."""

from __future__ import annotations

import logging

import httpx
from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core_api import flags
from core_api.errors import ApiError
from core_api.models import FeatureFlag
from core_api.schema import err
from social.models import Report

from . import services
from .context import describe
from .models import AllowlistEntry, Appeal, AuditEntry, ModerationAction
from .permissions import NotSuspended

log = logging.getLogger(__name__)
Dict = serializers.DictField()
DictList = serializers.ListField(child=serializers.DictField())


class StaffView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser, NotSuspended]


def _action(a: ModerationAction) -> dict:
    ap = getattr(a, "appeal", None)
    return {
        "id": str(a.pk),
        "kind": a.kind,
        "reason": a.reason,
        "created_at": a.created_at,
        "expires_at": a.expires_at,
        "lifted": a.lifted_at is not None,
        "appeal": {"status": ap.status, "note": ap.decision_note} if ap else None,
    }


class ReportQueueView(StaffView):
    @extend_schema(
        tags=["moderation"],
        responses={200: inline_serializer("ReportQueue", {"results": DictList})},
    )
    def get(self, request):
        status = request.query_params.get("status", "open")
        rows = (
            Report.objects.select_related("reporter")
            .filter(status=status)
            .order_by("created_at")[:100]
        )
        out = []
        for r in rows:
            out.append(
                {
                    "id": str(r.pk),
                    "target_type": r.target_type,
                    "reason": r.reason,
                    "details": r.details,
                    "created_at": r.created_at,
                    "reporter": r.reporter.username if r.reporter else None,
                    **describe(r),
                }
            )
        return Response({"results": out})


class ReportActionView(StaffView):
    @extend_schema(
        tags=["moderation"],
        request=inline_serializer(
            "ModerationDecision",
            {
                "kind": serializers.ChoiceField(
                    choices=["dismiss", "warn", "mute", "suspend", "ban"]
                ),
                "reason": serializers.CharField(required=False, allow_blank=True),
                "days": serializers.IntegerField(required=False, min_value=1, max_value=365),
            },
        ),
        responses={204: None, 400: err("VALIDATION_ERROR"), 404: err("NOT_FOUND")},
    )
    def post(self, request, report_id):
        r = Report.objects.filter(pk=report_id, status="open").first()
        if r is None:
            raise ApiError("NOT_FOUND", "That report has already been handled.", 404)
        kind = request.data.get("kind")
        if kind == "dismiss":
            services.dismiss(request.user, r)
            return Response(status=204)
        who = describe(r)["responsible"]
        user = User.objects.filter(pk=who["id"]).first() if who else None
        if user is None:
            raise ApiError("NOT_FOUND", "There's no account to act on.", 404)
        days = request.data.get("days")
        services.act(
            request.user,
            user,
            kind,
            str(request.data.get("reason") or ""),
            int(days) if days else None,
            report=r,
        )
        return Response(status=204)


class AppealQueueView(StaffView):
    @extend_schema(
        tags=["moderation"],
        responses={200: inline_serializer("AppealQueue", {"results": DictList})},
    )
    def get(self, request):
        rows = (
            Appeal.objects.select_related("action__user")
            .filter(status="open")
            .order_by("created_at")
        )
        return Response(
            {
                "results": [
                    {
                        "id": str(a.pk),
                        "text": a.text,
                        "created_at": a.created_at,
                        "user": {"id": str(a.action.user_id), "username": a.action.user.username},
                        "action": _action(a.action),
                    }
                    for a in rows
                ]
            }
        )


class AppealDecideView(StaffView):
    @extend_schema(
        tags=["moderation"],
        request=inline_serializer(
            "AppealDecision",
            {
                "overturn": serializers.BooleanField(),
                "note": serializers.CharField(required=False, allow_blank=True),
            },
        ),
        responses={204: None, 404: err("NOT_FOUND")},
    )
    def post(self, request, appeal_id):
        ap = Appeal.objects.select_related("action__user").filter(pk=appeal_id).first()
        if ap is None:
            raise ApiError("NOT_FOUND", "We couldn't find that appeal.", 404)
        services.decide(
            request.user,
            ap,
            bool(request.data.get("overturn")),
            str(request.data.get("note") or ""),
        )
        return Response(status=204)


class AuditView(StaffView):
    @extend_schema(
        tags=["moderation"], responses={200: inline_serializer("AuditLog", {"results": DictList})}
    )
    def get(self, request):
        rows = AuditEntry.objects.select_related("actor")[:200]
        return Response(
            {
                "results": [
                    {
                        "at": e.created_at,
                        "actor": e.actor.username if e.actor else None,
                        "action": e.action,
                        "target": e.target,
                        "details": e.details,
                    }
                    for e in rows
                ]
            }
        )


class AdminFlagsView(StaffView):
    @extend_schema(
        tags=["admin"], responses={200: inline_serializer("AdminFlags", {"results": DictList})}
    )
    def get(self, request):
        return Response(
            {
                "results": [
                    {"name": f.name, "enabled": f.enabled, "public": f.public, "note": f.note}
                    for f in FeatureFlag.objects.order_by("name")
                ]
            }
        )

    @extend_schema(
        tags=["admin"],
        operation_id="admin_flags_set",
        request=inline_serializer(
            "SetFlag", {"name": serializers.CharField(), "enabled": serializers.BooleanField()}
        ),
        responses={204: None, 404: err("NOT_FOUND")},
    )
    def put(self, request):
        f = FeatureFlag.objects.filter(name=request.data.get("name")).first()
        if f is None:
            raise ApiError("NOT_FOUND", "No such flag.", 404)
        f.enabled = bool(request.data.get("enabled"))
        f.save(update_fields=["enabled", "updated_at"])
        flags.invalidate()
        services.audit(request.user, "flag.set", f"flag:{f.name}", enabled=f.enabled)
        return Response(status=204)


class AdminBudgetsView(StaffView):
    """JNG-12-04: per-source budgets and live usage, read from ingest-ml."""

    @extend_schema(
        tags=["admin"],
        responses={
            200: inline_serializer(
                "Budgets", {"sources": DictList, "available": serializers.BooleanField()}
            )
        },
    )
    def get(self, request):
        try:
            r = httpx.get(
                f"{settings.INGEST_INTERNAL_URL.rstrip('/')}/internal/budgets",
                headers={"X-Service-Token": settings.SERVICE_TOKEN},
                timeout=3.0,
            )
            r.raise_for_status()
            return Response({"available": True, **r.json()})
        except httpx.HTTPError:
            log.warning("ingest budgets unavailable")
            return Response({"available": False, "sources": []})


class AdminAllowlistView(StaffView):
    @extend_schema(
        tags=["admin"],
        responses={
            200: inline_serializer(
                "Allowlist",
                {
                    "emails": serializers.ListField(child=serializers.EmailField()),
                    "max": serializers.IntegerField(),
                    "from_env": serializers.ListField(child=serializers.CharField()),
                },
            )
        },
    )
    def get(self, request):
        env = [e.strip().lower() for e in settings.SPOTIFY_ALLOWLIST.split(",") if e.strip()]
        return Response(
            {
                "emails": list(
                    AllowlistEntry.objects.order_by("email").values_list("email", flat=True)
                ),
                "max": services.SPOTIFY_ALLOWLIST_MAX,
                "from_env": env,
            }
        )

    @extend_schema(
        tags=["admin"],
        operation_id="admin_allowlist_add",
        request=inline_serializer("AllowlistAdd", {"email": serializers.EmailField()}),
        responses={204: None, 409: err("ALLOWLIST_FULL")},
    )
    def post(self, request):
        services.allowlist_add(request.user, str(request.data.get("email") or ""))
        return Response(status=204)

    @extend_schema(
        tags=["admin"],
        operation_id="admin_allowlist_remove",
        request=inline_serializer("AllowlistRemove", {"email": serializers.EmailField()}),
        responses={204: None},
    )
    def delete(self, request):
        services.allowlist_remove(request.user, str(request.data.get("email") or ""))
        return Response(status=204)


class MyModerationView(APIView):
    @extend_schema(
        tags=["moderation"],
        responses={200: inline_serializer("MyModeration", {"actions": DictList})},
    )
    def get(self, request):
        rows = ModerationAction.objects.filter(user=request.user).order_by("-created_at")[:20]
        return Response({"actions": [_action(a) for a in rows]})


class AppealView(APIView):
    @extend_schema(
        tags=["moderation"],
        request=inline_serializer("CreateAppeal", {"text": serializers.CharField(max_length=1000)}),
        responses={201: None, 404: err("NOT_FOUND"), 409: err("ALREADY_APPEALED")},
    )
    def post(self, request, action_id):
        a = ModerationAction.objects.filter(pk=action_id).first()
        if a is None:
            raise ApiError("NOT_FOUND", "We couldn't find that action.", 404)
        services.appeal(request.user, a, str(request.data.get("text") or ""))
        return Response(status=201)
