"""FeedCard resolution (CONTRACTS.md §7; SRS BR-01, BR-02, BR-03, BR-05, BR-14; JNG-05-01).

Precedence: LIVE > newest RECENT > TOP (last 30 days) > HIDDEN.

* LIVE only if ``np:{owner}`` exists AND its signal is < 90 s old AND the route is live-capable
  (``jingle_common.enums.is_live_capable``). Apple/Amazon direct and exports are never Live.
* ``via`` is read from Redis for the checks above and **never** leaves this module (BR-14).
* ``attribution == "SPOTIFY"`` iff the data came from the direct Spotify API (BR-03).
* Privacy: Private mode or ``activity_visibility = nobody`` hides the card from everyone but the
  owner; ``show_last_active = False`` drops ``observed_at`` and uses "Recently on …".
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import redis
from jingle_common.enums import (
    LIVE_MAX_AGE_SECONDS,
    CardState,
    Platform,
    Via,
    is_live_capable,
)
from jingle_common.labels import freshness_label

from accounts.models import PrivacySettings
from core_api import policy
from core_api.mongo import get_db
from core_api.redis_client import get_redis

log = logging.getLogger(__name__)

TOP_WINDOW_DAYS = 30
LINK_PLATFORMS = ("SPOTIFY", "APPLE_MUSIC", "AMAZON_MUSIC", "YOUTUBE_MUSIC")


@dataclass
class Signal:
    """One play signal read from ``np``/``last`` (Redis) or a Mongo listen."""

    event: dict[str, Any]
    observed_at: datetime | None
    via: Via | None
    platform: Platform

    @property
    def is_spotify_direct(self) -> bool:
        return self.via is Via.DIRECT and self.platform is Platform.SPOTIFY


def _platform(value: Any) -> Platform:
    try:
        return Platform(str(value))
    except ValueError:
        return Platform.UNKNOWN


def _via(value: Any) -> Via | None:
    try:
        return Via(str(value))
    except ValueError:
        return None


def _epoch(value: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(float(value), tz=UTC)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _signal_from_hash(h: dict[str, str]) -> Signal | None:
    if not h:
        return None
    try:
        event = json.loads(h.get("event") or "{}")
    except (TypeError, ValueError):
        event = {}
    if not isinstance(event, dict):
        event = {}
    return Signal(
        event=event,
        observed_at=_epoch(h.get("observed_at")),
        via=_via(h.get("via") or event.get("via")),
        platform=_platform(h.get("platform") or event.get("platform")),
    )


def _signal_from_listen(doc: dict[str, Any]) -> Signal:
    meta = doc.get("meta") or {}
    observed = doc.get("observed_at") or doc.get("played_at")
    if isinstance(observed, datetime) and observed.tzinfo is None:
        observed = observed.replace(tzinfo=UTC)
    if not isinstance(observed, datetime):
        observed = None
    return Signal(
        event=doc,
        observed_at=observed,
        via=_via(doc.get("via") or meta.get("via")),
        platform=_platform(doc.get("platform") or meta.get("platform")),
    )


def _user_match(owner_id: str) -> dict:
    return {"$or": [{"user_id": owner_id}, {"meta.user_id": owner_id}]}


def _top_signal(owner_id: str, now: datetime) -> tuple[Signal | None, bool]:
    """Most-played track in the last 30 days. Returns (signal, degraded)."""
    db = get_db()
    if db is None:
        return None, True
    since = now - timedelta(days=TOP_WINDOW_DAYS)
    pipeline = [
        {"$match": {**_user_match(owner_id), "played_at": {"$gte": since}}},
        {"$sort": {"played_at": -1}},
        {
            "$group": {
                "_id": {
                    "$ifNull": [
                        "$recording_id",
                        {"$concat": [{"$toLower": "$raw.artist"}, "|", {"$toLower": "$raw.title"}]},
                    ]
                },
                "plays": {"$sum": 1},
                "doc": {"$first": "$$ROOT"},
            }
        },
        {"$sort": {"plays": -1}},
        {"$limit": 1},
    ]
    try:
        rows = list(db.listens.aggregate(pipeline))
    except Exception:  # noqa: BLE001
        log.warning("top-tracks aggregation failed")
        return None, True
    if not rows:
        return None, False
    return _signal_from_listen(rows[0]["doc"]), False


def _latest_listen(owner_id: str) -> Signal | None:
    """Degraded-mode fallback when Redis is down (Technical Bible 9.4)."""
    db = get_db()
    if db is None:
        return None
    try:
        doc = db.listens.find_one(_user_match(owner_id), sort=[("played_at", -1)])
    except Exception:  # noqa: BLE001
        return None
    return _signal_from_listen(doc) if doc else None


def _links(recording_id: str | None) -> dict[str, str | None]:
    links: dict[str, str | None] = dict.fromkeys(LINK_PLATFORMS)
    if not recording_id:
        return links
    try:
        rid = uuid.UUID(str(recording_id))
    except ValueError:
        return links
    from sources.models import RecordingLink

    for platform, url in RecordingLink.objects.filter(recording_id=rid).values_list(
        "platform", "url"
    ):
        if platform in links:
            links[platform] = url
    return links


_SEARCH = {
    "SPOTIFY": "https://open.spotify.com/search/{q}",
    "APPLE_MUSIC": "https://music.apple.com/search?term={q}",
    "YOUTUBE_MUSIC": "https://music.youtube.com/search?q={q}",
    "AMAZON_MUSIC": "https://music.amazon.com/search/{q}",
}


def _search_links(title: str, artist: str) -> dict[str, str]:
    """JNG-06-03 fallback: a search on each platform when no verified link exists."""
    from urllib.parse import quote

    q = quote(f"{title} {artist}".strip()[:200])
    return {p: url.format(q=q) for p, url in _SEARCH.items()} if q else {}


def _recording(signal: Signal) -> dict[str, Any]:
    ev = signal.event
    raw = ev.get("raw") or {}
    rid = ev.get("recording_id")
    return {
        "id": str(rid) if rid else None,
        "title": raw.get("title") or "",
        "artist": raw.get("artist") or "",
        "album": raw.get("album") or None,
        "artwork_url": ev.get("artwork_url") or None,
        "links": _links(rid),
        "search_links": _search_links(raw.get("title") or "", raw.get("artist") or ""),
    }


def _friend(owner) -> dict[str, Any]:
    return {
        "id": str(owner.pk),
        "username": owner.username,
        "display_name": owner.display_name or owner.username,
        "avatar_url": None,
    }


def hidden_card(owner, degraded: bool = False) -> dict[str, Any]:
    return {
        "friend": _friend(owner),
        "state": CardState.HIDDEN.value,
        "platform": None,
        "recording": None,
        "freshness_label": freshness_label(CardState.HIDDEN, Platform.UNKNOWN, None, _now()),
        "degraded": degraded,
        "attribution": None,
    }


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _is_live(signal: Signal | None, now: datetime) -> bool:
    if signal is None or signal.observed_at is None or signal.via is None:
        return False
    age = (now - signal.observed_at).total_seconds()
    if age >= LIVE_MAX_AGE_SECONDS or age < -LIVE_MAX_AGE_SECONDS:
        return False
    return is_live_capable(signal.via, signal.platform)


def _newest(*signals: Signal | None) -> Signal | None:
    present = [s for s in signals if s is not None and s.event]
    if not present:
        return None
    epoch = datetime.min.replace(tzinfo=UTC)
    return max(present, key=lambda s: s.observed_at or epoch)


def _source_delayed(owner, platform: Platform) -> bool:
    """NFR-AVAIL-03: a platform whose route needs reconnecting shows cached plays as delayed."""
    from sources.models import PlatformConnection, SourceStatus

    return PlatformConnection.objects.filter(
        user=owner,
        platform=platform.value,
        status__in=[SourceStatus.NEEDS_REAUTH, SourceStatus.ERROR],
    ).exists()


def resolve_card(owner, viewer, now: datetime | None = None) -> dict[str, Any]:
    """Build the FeedCard of ``owner`` as seen by ``viewer`` (CONTRACTS.md §7)."""
    now = now or _now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    is_owner = viewer is not None and str(viewer.pk) == str(owner.pk)
    if not policy.can_view_activity(viewer, owner, now):
        return hidden_card(owner)

    owner_id = str(owner.pk)
    degraded = False
    np_sig = last_sig = None
    try:
        r = get_redis()
        pipe = r.pipeline()
        pipe.hgetall(f"np:{owner_id}")
        pipe.hgetall(f"last:{owner_id}")
        np_hash, last_hash = pipe.execute()
        np_sig, last_sig = _signal_from_hash(np_hash), _signal_from_hash(last_hash)
    except redis.RedisError:
        log.warning("redis unavailable; card degraded")
        degraded = True
        last_sig = _latest_listen(owner_id)

    if _is_live(np_sig, now):
        state, signal = CardState.LIVE, np_sig
    else:
        signal = _newest(np_sig, last_sig)
        state = CardState.RECENT
        if signal is None:
            signal, top_degraded = _top_signal(owner_id, now)
            degraded = degraded or top_degraded
            state = CardState.TOP
    if signal is None:
        return hidden_card(owner, degraded=degraded)

    precise = is_owner or PrivacySettings.for_user(owner).show_last_active
    card: dict[str, Any] = {
        "friend": _friend(owner),
        "state": state.value,
        "platform": signal.platform.value,
        "recording": _recording(signal),
    }
    if precise and state is not CardState.TOP and signal.observed_at is not None:
        card["observed_at"] = _iso(signal.observed_at)
    card["freshness_label"] = freshness_label(
        state, signal.platform, signal.observed_at, now, show_precise_time=precise
    )
    card["degraded"] = degraded or (
        state is CardState.RECENT and _source_delayed(owner, signal.platform)
    )
    card["attribution"] = "SPOTIFY" if signal.is_spotify_direct else None
    return card
