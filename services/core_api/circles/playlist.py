"""Circle shared playlist (JNG-04-08).

Members see and add; the adder or the circle's owner/admins remove. One entry per song (the same
song from any app merges). Muted accounts can't add. Songs added by someone you blocked (either
way) are hidden from you, like everything else in circles (BR-07).
"""

from __future__ import annotations

from django.db import IntegrityError, transaction

from accounts.validators import contains_profanity
from core_api.errors import ApiError
from social.services import blocked_ids

from . import services
from .models import Circle, CirclePlaylistItem, Role


def items(circle: Circle, viewer) -> list[CirclePlaylistItem]:
    services.require_member(circle, viewer)
    hidden = blocked_ids(viewer.pk)
    return list(
        circle.playlist.select_related("added_by")
        .exclude(added_by_id__in=hidden)
        .order_by("added_at")  # oldest first: the order you see is the order exported
    )


def add(
    circle: Circle, user, *, title: str, artist: str, note: str = "", recording_id=None
) -> CirclePlaylistItem:
    from artwork.services import track_key
    from moderation.services import require_not_muted

    services.require_member(circle, user)
    require_not_muted(user)
    title, artist, note = (
        (title or "").strip()[:500],
        (artist or "").strip()[:500],
        (note or "").strip(),
    )
    if not title or not artist:
        raise ApiError("VALIDATION_ERROR", "Pick a song to add.", 400)
    if len(note) > CirclePlaylistItem.NOTE_MAX:
        raise ApiError(
            "VALIDATION_ERROR",
            f"Keep the note under {CirclePlaylistItem.NOTE_MAX} characters.",
            400,
        )
    if note and contains_profanity(note):
        raise ApiError("VALIDATION_ERROR", "Please choose different wording.", 400)
    if circle.playlist.count() >= CirclePlaylistItem.MAX_ITEMS:
        raise ApiError(
            "PLAYLIST_FULL", f"This playlist is full ({CirclePlaylistItem.MAX_ITEMS} songs).", 409
        )
    recording = None
    if recording_id:
        from sources.models import Recording

        recording = Recording.objects.filter(pk=recording_id).first()
    try:
        with transaction.atomic():
            return CirclePlaylistItem.objects.create(
                circle=circle,
                added_by=user,
                recording=recording,
                track_key=track_key(title, artist),
                title=title,
                artist=artist,
                note=note,
            )
    except IntegrityError:
        raise ApiError(
            "ALREADY_IN_PLAYLIST", "That song is already in the playlist.", 409
        ) from None


def remove(circle: Circle, user, item_id) -> None:
    m = services.require_member(circle, user)
    item = circle.playlist.filter(pk=item_id).first()
    if item is None:
        raise ApiError("NOT_FOUND", "That song isn't in the playlist.", 404)
    if item.added_by_id != user.pk and m.role not in (Role.OWNER, Role.ADMIN):
        raise ApiError("FORBIDDEN", "Only whoever added it, or a circle admin, can remove it.", 403)
    item.delete()
