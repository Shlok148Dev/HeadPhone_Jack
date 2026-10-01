"""Notifications API (EP-11: JNG-11-01…04, 07)."""

from __future__ import annotations

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from core_api.errors import ApiError
from core_api.schema import err

from .models import (
    LABELS,
    PUSH_CAP_DEFAULT,
    PUSH_CAP_MAX,
    TYPES,
    Notification,
    NotificationPrefs,
    PushSubscription,
    default_types,
)


class NotificationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    type = serializers.CharField()
    title = serializers.CharField()
    url = serializers.CharField()
    created_at = serializers.DateTimeField()
    read = serializers.BooleanField()


class SettingsSerializer(serializers.Serializer):
    types = serializers.DictField()
    labels = serializers.DictField(read_only=True)
    quiet_start = serializers.RegexField(r"^([01]\d|2[0-3]):[0-5]\d$")
    quiet_end = serializers.RegexField(r"^([01]\d|2[0-3]):[0-5]\d$")
    tz = serializers.CharField(max_length=64)
    push_daily_cap = serializers.IntegerField(min_value=1, max_value=PUSH_CAP_MAX)
    push_available = serializers.BooleanField(read_only=True)
    push_subscribed = serializers.BooleanField(read_only=True)


def _payload(n: Notification) -> dict:
    return {
        "id": n.pk,
        "type": n.type,
        "title": n.title,
        "url": n.url,
        "created_at": n.created_at,
        "read": n.read_at is not None,
    }


def _settings(user) -> dict:
    p = NotificationPrefs.for_user(user.pk)
    return {
        "types": {**default_types(), **(p.types or {})},
        "labels": LABELS,
        "quiet_start": p.quiet_start,
        "quiet_end": p.quiet_end,
        "tz": p.tz,
        "push_daily_cap": p.push_daily_cap,
        "push_available": bool(settings.VAPID_PUBLIC_KEY),
        "push_subscribed": PushSubscription.objects.filter(user=user).exists(),
    }


class NotificationsView(APIView):
    @extend_schema(
        tags=["notifications"],
        responses={
            200: inline_serializer(
                "NotificationList",
                {
                    "unread": serializers.IntegerField(),
                    "results": NotificationSerializer(many=True),
                },
            )
        },
    )
    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        return Response(
            {
                "unread": qs.filter(read_at__isnull=True).count(),
                "results": [_payload(n) for n in qs.order_by("-created_at")[:50]],
            }
        )


class ReadView(APIView):
    @extend_schema(
        tags=["notifications"],
        request=inline_serializer(
            "MarkRead",
            {"ids": serializers.ListField(child=serializers.UUIDField(), required=False)},
        ),
        responses={204: None},
    )
    def post(self, request):
        qs = Notification.objects.filter(user=request.user, read_at__isnull=True)
        ids = request.data.get("ids")
        if isinstance(ids, list) and ids:
            qs = qs.filter(pk__in=ids)
        qs.update(read_at=timezone.now())
        return Response(status=204)


class SettingsView(APIView):
    @extend_schema(
        tags=["notifications"],
        operation_id="notification_settings_get",
        responses={200: SettingsSerializer},
    )
    def get(self, request):
        return Response(_settings(request.user))

    @extend_schema(
        tags=["notifications"],
        operation_id="notification_settings_update",
        request=SettingsSerializer,
        responses={200: SettingsSerializer, 400: err("VALIDATION_ERROR")},
    )
    def put(self, request):
        from zoneinfo import ZoneInfo

        ser = SettingsSerializer(data={**_settings(request.user), **request.data})
        if not ser.is_valid():
            raise ApiError(
                "VALIDATION_ERROR", "Check your notification settings.", 400, details=ser.errors
            )
        d = ser.validated_data
        try:
            ZoneInfo(d["tz"])
        except Exception:  # noqa: BLE001
            raise ApiError("VALIDATION_ERROR", "Unknown time zone.", 400) from None
        types = default_types()
        for t, v in (d["types"] or {}).items():
            if t in TYPES and isinstance(v, dict):
                types[t] = {
                    "in_app": bool(v.get("in_app", True)),
                    "push": bool(v.get("push", True)),
                }
        p = NotificationPrefs.for_user(request.user.pk)
        p.types, p.quiet_start, p.quiet_end, p.tz = types, d["quiet_start"], d["quiet_end"], d["tz"]
        p.push_daily_cap = d.get("push_daily_cap") or PUSH_CAP_DEFAULT
        p.save()
        return Response(_settings(request.user))


class PushSubscriptionView(APIView):
    @extend_schema(
        tags=["notifications"],
        request=inline_serializer(
            "PushSubscribe",
            {
                "endpoint": serializers.URLField(),
                "keys": inline_serializer(
                    "PushKeys", {"p256dh": serializers.CharField(), "auth": serializers.CharField()}
                ),
            },
        ),
        responses={204: None, 400: err("VALIDATION_ERROR")},
    )
    def post(self, request):
        """JNG-11-02: stored only after the person allowed push in their browser."""
        if not settings.VAPID_PUBLIC_KEY:
            raise ApiError(
                "PUSH_UNAVAILABLE", "Push notifications aren't set up on this server.", 400
            )
        endpoint = str(request.data.get("endpoint") or "")
        keys = request.data.get("keys") or {}
        if not endpoint.startswith("https://") or not keys.get("p256dh") or not keys.get("auth"):
            raise ApiError("VALIDATION_ERROR", "That push subscription isn't valid.", 400)
        PushSubscription.objects.update_or_create(
            endpoint=endpoint[:800],
            defaults={
                "user": request.user,
                "p256dh": str(keys["p256dh"])[:200],
                "auth": str(keys["auth"])[:100],
            },
        )
        return Response(status=204)

    @extend_schema(tags=["notifications"], operation_id="push_unsubscribe", responses={204: None})
    def delete(self, request):
        PushSubscription.objects.filter(user=request.user).delete()
        return Response(status=204)


class PushKeyView(APIView):
    @extend_schema(
        tags=["notifications"],
        responses={
            200: inline_serializer(
                "PushKey",
                {"available": serializers.BooleanField(), "public_key": serializers.CharField()},
            )
        },
    )
    def get(self, request):
        return Response(
            {"available": bool(settings.VAPID_PUBLIC_KEY), "public_key": settings.VAPID_PUBLIC_KEY}
        )
