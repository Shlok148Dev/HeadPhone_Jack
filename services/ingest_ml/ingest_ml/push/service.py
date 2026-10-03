"""Turn a ListenBrainz submission into plays and record them (ADR-0003, ADR-0014).

Every push to Jingle's endpoint is the COMPANION route, whichever client sent it.
``observed_at`` is always the server receive time; the client's clock only sets ``played_at``.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from jingle_common.enums import EventKind, Platform
from jingle_common.events import ListenEvent, RawTrack

from ..adapters.base import COMPANION_ROUTE
from ..db import now
from ..record import (
    DEDUPE_TTL_SECONDS,
    NP_TTL_SECONDS,
    STREAM,
    STREAM_RETENTION,
    Play,
    last_key,
    np_key,
    record_plays,
)
from ..resources import Resources
from .platform import infer_platform, safe_platform_url, spotify_url
from .schemas import Listen, Submission

__all__ = [
    "DEDUPE_TTL_SECONDS",
    "MAX_FUTURE",
    "NP_TTL_SECONDS",
    "STREAM",
    "STREAM_RETENTION",
    "PushRejected",
    "ingest_submission",
    "last_key",
    "np_key",
]

MAX_FUTURE = timedelta(minutes=5)


class PushRejected(Exception):
    """The submission violates an ingest rule; nothing was written."""


def _links(listen: Listen, platform: Platform) -> dict[Platform, str]:
    ai = listen.track_metadata.additional_info
    links: dict[Platform, str] = {}
    if url := safe_platform_url(ai.origin_url, platform):
        links[platform] = url
    if url := spotify_url(ai.spotify_id):
        links[Platform.SPOTIFY] = url
    return links


def to_plays(sub: Submission, received_at: datetime) -> list[Play]:
    """Validate everything before any write."""
    plays: list[Play] = []
    for listen in sub.payload:
        tm = listen.track_metadata
        ai = tm.additional_info
        if listen.listened_at is not None:
            try:
                played_at = datetime.fromtimestamp(listen.listened_at, UTC)
            except (OverflowError, OSError, ValueError):
                raise PushRejected("listened_at is out of range") from None
            if played_at > received_at + MAX_FUTURE:
                raise PushRejected("listened_at is more than 5 minutes in the future")
        else:
            played_at = received_at
        platform = infer_platform(ai.music_service, ai.origin_url, ai.music_service_name)
        plays.append(
            Play(
                track=RawTrack(
                    artist=tm.artist_name,
                    title=tm.track_name,
                    album=tm.release_name,
                    duration_ms=ai.effective_duration_ms,
                ),
                played_at=played_at,
                platform=platform,
                isrc=ai.isrc,
                recording_mbid=ai.recording_uuid,
                release_mbid=ai.release_uuid,
                links=_links(listen, platform),
            )
        )
    return plays


async def ingest_submission(
    res: Resources, user_id: UUID, sub: Submission, received_at: datetime | None = None
) -> list[ListenEvent]:
    received_at = received_at or now()
    plays = to_plays(sub, received_at)
    kind = EventKind.NOW_PLAYING if sub.listen_type == "playing_now" else EventKind.LISTEN
    return await record_plays(
        res,
        user_id,
        plays,
        kind=kind,
        route=COMPANION_ROUTE,
        via=COMPANION_ROUTE.via,
        received_at=received_at,
        allow_remote=sub.listen_type != "import",
    )
