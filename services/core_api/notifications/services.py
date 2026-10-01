"""One way to tell someone something (EP-11). Every notification goes through ``notify``."""

from __future__ import annotations

import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from core_api import events
from core_api.redis_client import get_redis

from .models import TYPES, Notification, NotificationPrefs, PushSubscription

log = logging.getLogger(__name__)


def _hm(s: str) -> time:
    h, m = (int(x) for x in (s or "00:00").split(":"))
    return time(h, m)


def in_quiet_hours(prefs: NotificationPrefs, now: datetime | None = None) -> bool:
    """JNG-11-04: default 23:00–08:00 in the person's own time zone (spans midnight)."""
    now = now or timezone.now()
    try:
        local = now.astimezone(ZoneInfo(prefs.tz)).time()
    except Exception:  # noqa: BLE001 - bad tz: fall back to IST
        local = now.astimezone(ZoneInfo("Asia/Kolkata")).time()
    start, end = _hm(prefs.quiet_start), _hm(prefs.quiet_end)
    if start == end:
        return False
    return start <= local or local < end if start > end else start <= local < end


def _push_budget(user_id, cap: int, now: datetime) -> bool:
    """JNG-11-07: at most ``cap`` pushes a day (5 unless the person raised it)."""
    key = f"pushcount:{user_id}:{now.astimezone(ZoneInfo('Asia/Kolkata')).date().isoformat()}"
    try:
        r = get_redis()
        n = r.incr(key)
        if n == 1:
            r.expire(key, 2 * 86400)
        return n <= cap
    except Exception:  # noqa: BLE001 - no Redis: don't push rather than risk spamming
        return False


def notify(
    user_id, type_: str, title: str, url: str = "", now: datetime | None = None
) -> Notification | None:
    """In-app row + realtime hint; web push only if allowed, outside quiet hours, under the cap."""
    if type_ not in TYPES:
        raise ValueError(f"unknown notification type {type_!r}")
    now = now or timezone.now()
    prefs = NotificationPrefs.for_user(user_id)
    n = None
    if prefs.allows(type_, "in_app"):
        n = Notification.objects.create(
            user_id=user_id, type=type_, title=title[:200], url=url[:300]
        )
        transaction.on_commit(
            lambda: events.publish_domain(
                "notify", {"user_id": str(user_id), "type": type_, "id": str(n.pk)}
            )
        )
    if (
        n is not None
        and prefs.allows(type_, "push")
        and PushSubscription.objects.filter(user_id=user_id).exists()
        and not in_quiet_hours(prefs, now)
        and _push_budget(user_id, prefs.push_daily_cap, now)
    ):
        from .tasks import push

        transaction.on_commit(lambda: push.delay(str(n.pk)))
    return n


def send_push(notification_id: str) -> int:
    """Deliver one notification to every browser the person allowed. Needs VAPID keys (.env)."""
    import json

    from django.conf import settings

    n = Notification.objects.filter(pk=notification_id).first()
    if n is None or not settings.VAPID_PRIVATE_KEY:
        return 0
    from pywebpush import WebPushException, webpush

    sent = 0
    for sub in PushSubscription.objects.filter(user_id=n.user_id):
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=json.dumps({"title": n.title, "url": n.url or "/notifications"}),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
                ttl=3600,
            )
            sent += 1
        except WebPushException as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (404, 410):
                sub.delete()  # the browser dropped this subscription
            else:
                log.warning("push failed", extra={"status": status})
    if sent:
        Notification.objects.filter(pk=n.pk).update(pushed_at=timezone.now())
    return sent
