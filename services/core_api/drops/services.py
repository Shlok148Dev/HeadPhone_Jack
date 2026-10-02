"""Daily Drop rules (JNG-14-01).

- One drop per person per local day; it can't be changed (the point is choosing).
- Friends' drops for today are revealed only after you drop yours. Before that you see who
  dropped, not what (the pull to take part). Blocks hide both ways (BR-07).
- Streak: consecutive local days with a drop, ending today, or yesterday if today is still open.
"""

from __future__ import annotations

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.validators import contains_profanity
from core_api.errors import ApiError
from social.services import blocked_ids, friend_ids

from .models import NOTE_MAX, Drop


def tz_of(user) -> ZoneInfo:
    from notifications.models import NotificationPrefs

    name = (
        NotificationPrefs.objects.filter(user=user).values_list("tz", flat=True).first()
        or settings.TIME_ZONE
    )
    try:
        return ZoneInfo(name)
    except Exception:  # noqa: BLE001 - a bad stored zone must not break the day
        return ZoneInfo(settings.TIME_ZONE)


def today_for(user, now=None) -> date:
    return (now or timezone.now()).astimezone(tz_of(user)).date()


def create(user, *, title: str, artist: str, note: str = "", recording_id=None, now=None) -> Drop:
    title, artist, note = title.strip()[:500], artist.strip()[:500], note.strip()
    if not title or not artist:
        raise ApiError("VALIDATION_ERROR", "Pick a song to drop.", 400)
    if len(note) > NOTE_MAX:
        raise ApiError("VALIDATION_ERROR", f"Keep the note under {NOTE_MAX} characters.", 400)
    if note and contains_profanity(note):
        raise ApiError("VALIDATION_ERROR", "Please choose different wording.", 400)
    recording = None
    if recording_id:
        from sources.models import Recording

        recording = Recording.objects.filter(pk=recording_id).first()
    try:
        with transaction.atomic():
            return Drop.objects.create(
                user=user,
                day=today_for(user, now),
                recording=recording,
                title=title,
                artist=artist,
                note=note,
            )
    except IntegrityError:
        raise ApiError("ALREADY_DROPPED", "You've already dropped today's song.", 409) from None


def streak(user, now=None) -> int:
    today = today_for(user, now)
    days = set(
        Drop.objects.filter(user=user, day__gte=today - timedelta(days=400)).values_list(
            "day", flat=True
        )
    )
    d = today if today in days else today - timedelta(days=1)
    n = 0
    while d in days:
        n += 1
        d -= timedelta(days=1)
    return n


def friends_today(viewer, now=None) -> list[Drop]:
    """Friends' drops for the viewer's today, newest first, minus blocks (either way)."""
    ids = set(friend_ids(viewer.pk)) - blocked_ids(viewer.pk)
    return list(
        Drop.objects.filter(user_id__in=ids, day=today_for(viewer, now))
        .select_related("user")
        .order_by("-created_at")
    )
