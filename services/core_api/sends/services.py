"""Send rules (EP-06). Every send goes through ``send`` so recipient checks hold everywhere."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import UTC, timedelta

from django.db import transaction
from django.utils import timezone

from circles.models import CircleMember
from core_api import events, policy
from core_api.errors import ApiError
from social.services import blocked_ids

from .models import (
    CREDIT_WINDOW_DAYS,
    MAX_RECIPIENTS,
    MIXTAPE_MAX,
    MIXTAPE_MIN,
    NOTE_MAX,
    PLAYED_WINDOW_DAYS,
    REACTIONS,
    Delivery,
    Item,
    Kind,
    Recommendation,
)

log = logging.getLogger(__name__)


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def _key(artist: str, title: str) -> str:
    return f"{_norm(artist)}|{_norm(title)}"


def _items(raw_items: list[dict]) -> list[dict]:
    from sources.models import Recording

    if not (len(raw_items) == 1 or MIXTAPE_MIN <= len(raw_items) <= MIXTAPE_MAX):
        raise ApiError(
            "VALIDATION_ERROR",
            "Add at least 5 songs, or remove extras to send one song.",
            400,
        )
    out = []
    for raw in raw_items:
        rec = None
        rid = raw.get("recording_id")
        if rid:
            rec = Recording.objects.filter(pk=rid).first()
            if rec is None:
                raise ApiError("VALIDATION_ERROR", "We couldn't find one of those songs.", 400)
        title = (rec.title if rec else str(raw.get("title") or "")).strip()[:500]
        artist = (rec.artist_name if rec else str(raw.get("artist") or "")).strip()[:500]
        if not title or not artist:
            raise ApiError("VALIDATION_ERROR", "Each song needs a title and an artist.", 400)
        out.append({"recording": rec, "title": title, "artist": artist})
    if len({_key(i["artist"], i["title"]) for i in out}) != len(out):
        raise ApiError("VALIDATION_ERROR", "That mixtape has the same song twice.", 400)
    return out


def _recipients(sender, user_ids, circle_ids) -> list[tuple[str, str | None]]:
    """(recipient_id, circle_id) pairs: friends directly, or co-members of circles I'm in."""
    blocked = {str(b) for b in blocked_ids(sender.pk)}
    chosen: dict[str, str | None] = {}
    for cid in circle_ids:
        if not CircleMember.objects.filter(circle_id=cid, user=sender).exists():
            raise ApiError("NOT_FOUND", "We couldn't find that circle.", 404)
        for uid in CircleMember.objects.filter(circle_id=cid).values_list("user_id", flat=True):
            chosen.setdefault(str(uid), str(cid))
    for uid in user_ids:
        uid = str(uid)
        if uid in chosen:
            chosen[uid] = None  # picked by name as well: a direct send
            continue
        if not policy.are_friends(sender, uid):
            raise ApiError("NOT_FOUND", "You can only send to friends and your circles.", 404)
        chosen[uid] = None
    chosen.pop(str(sender.pk), None)
    for b in blocked:
        chosen.pop(b, None)
    if not chosen:
        raise ApiError("VALIDATION_ERROR", "Pick at least one friend or circle.", 400)
    if len(chosen) > MAX_RECIPIENTS:
        raise ApiError("VALIDATION_ERROR", f"You can send to up to {MAX_RECIPIENTS} people.", 400)
    return list(chosen.items())


@transaction.atomic
def send(
    sender, items, note: str = "", user_ids=(), circle_ids=(), reply_to: Delivery | None = None
) -> Recommendation:
    """JNG-06-01/02: a track or a 5–8 track mixtape, with an optional note, to friends/circles."""
    note = (note or "").strip()
    if len(note) > NOTE_MAX:
        raise ApiError("VALIDATION_ERROR", f"Notes can be up to {NOTE_MAX} characters.", 400)
    clean = _items(list(items))
    if reply_to is not None:
        # JNG-06-06: a song back goes to the person who sent it, and only them.
        if reply_to.recipient_id != sender.pk or policy.is_blocked_either_way(
            sender, reply_to.rec.sender_id
        ):
            raise ApiError("NOT_FOUND", "We couldn't find that send.", 404)
        recipients = [(str(reply_to.rec.sender_id), None)]
    else:
        recipients = _recipients(sender, user_ids, circle_ids)
    rec = Recommendation.objects.create(
        sender=sender,
        kind=Kind.TRACK if len(clean) == 1 else Kind.MIXTAPE,
        note=note,
        reply_to=reply_to,
    )
    Item.objects.bulk_create(Item(rec=rec, position=i, **it) for i, it in enumerate(clean))
    deliveries = Delivery.objects.bulk_create(
        Delivery(rec=rec, recipient_id=uid, circle_id=cid) for uid, cid in recipients
    )
    for d in deliveries:
        transaction.on_commit(
            lambda d=d: events.publish_domain(
                "notify", {"user_id": str(d.recipient_id), "type": "send", "id": str(d.pk)}
            )
        )
    return rec


def _status_changed(d: Delivery) -> None:
    events.publish_domain(
        "notify", {"user_id": str(d.rec.sender_id), "type": "send_status", "id": str(d.rec_id)}
    )


def mark_delivered(user) -> int:
    """Delivered = the recipient's app has fetched it (inbox or badge)."""
    rows = list(
        Delivery.objects.select_related("rec").filter(recipient=user, delivered_at__isnull=True)
    )
    if not rows:
        return 0
    Delivery.objects.filter(pk__in=[d.pk for d in rows]).update(delivered_at=timezone.now())
    for rec_id in {d.rec_id for d in rows}:
        d = next(x for x in rows if x.rec_id == rec_id)
        _status_changed(d)
    return len(rows)


def received(user, delivery_id) -> Delivery:
    d = Delivery.objects.select_related("rec").filter(pk=delivery_id, recipient=user).first()
    if d is None or policy.is_blocked_either_way(user, d.rec.sender_id):
        raise ApiError("NOT_FOUND", "We couldn't find that send.", 404)
    return d


def view(d: Delivery) -> Delivery:
    if d.viewed_at is None:
        now = timezone.now()
        d.viewed_at = now
        d.delivered_at = d.delivered_at or now
        d.save(update_fields=["viewed_at", "delivered_at"])
        _status_changed(d)
    return d


def react(d: Delivery, reaction: str) -> Delivery:
    if reaction and reaction not in REACTIONS:
        raise ApiError("VALIDATION_ERROR", "Pick one of the reactions.", 400)
    d.reaction = reaction
    d.reacted_at = timezone.now() if reaction else None
    d.save(update_fields=["reaction", "reacted_at"])
    if reaction:
        events.publish_domain(
            "notify", {"user_id": str(d.rec.sender_id), "type": "send_reaction", "id": str(d.pk)}
        )
    return view(d)


# ---- Played + discovery credit (ML/worker jobs) ---------------------------------------------


def _listen_match(user_id: str, since, until=None) -> dict:
    # Only listens we may analyse: never direct-Spotify API data (BR-03, Policy III).
    played = {"$gte": since}
    if until is not None:
        played["$lt"] = until
    return {
        "$or": [{"user_id": user_id}, {"meta.user_id": user_id}],
        "played_at": played,
        "analytics_allowed": {"$ne": False},
    }


def check_played(now=None) -> int:
    """JNG-06-04: Played when the recipient's own listens include the song after it was sent."""
    from core_api.mongo import get_db

    db = get_db()
    if db is None:
        return 0
    now = now or timezone.now()
    pending = (
        Delivery.objects.select_related("rec")
        .prefetch_related("rec__items")
        .filter(
            played_at__isnull=True,
            rec__created_at__gte=now - timedelta(days=PLAYED_WINDOW_DAYS),
        )
    )
    by_user: dict[str, list[Delivery]] = defaultdict(list)
    for d in pending:
        by_user[str(d.recipient_id)].append(d)
    marked = 0
    for uid, rows in by_user.items():
        since = min(d.rec.created_at for d in rows)
        try:
            docs = db.listens.find(
                _listen_match(uid, since),
                {"recording_id": 1, "raw.artist": 1, "raw.title": 1, "played_at": 1},
            )
            heard: dict[str, object] = {}
            for doc in docs:
                raw = doc.get("raw") or {}
                at = doc.get("played_at")
                for k in (
                    str(doc.get("recording_id") or ""),
                    _key(raw.get("artist"), raw.get("title")),
                ):
                    if k and (k not in heard or at < heard[k]):
                        heard[k] = at
        except Exception:  # noqa: BLE001
            log.warning("played check failed for a user")
            continue
        for d in rows:
            for it in d.rec.items.all():
                keys = [str(it.recording_id or ""), _key(it.artist, it.title)]
                at = next((heard[k] for k in keys if k and k in heard), None)
                if at is not None and _aware(at) >= d.rec.created_at:
                    Delivery.objects.filter(pk=d.pk).update(
                        played_at=_aware(at), delivered_at=d.delivered_at or _aware(at)
                    )
                    _status_changed(d)
                    marked += 1
                    break
    return marked


def _aware(dt):
    return dt if timezone.is_aware(dt) else dt.replace(tzinfo=UTC)


def _artist_counts(db, uid: str, since, until) -> Counter:
    rows = db.listens.aggregate(
        [
            {"$match": _listen_match(uid, since, until)},
            {"$group": {"_id": {"$toLower": "$raw.artist"}, "n": {"$sum": 1}}},
        ]
    )
    return Counter({_norm(r["_id"] or ""): r["n"] for r in rows if r.get("_id")})


def discovery_credits(now=None) -> int:
    """JNG-06-05 / Tech Bible 6.4: the sent artist entered the friend's top 20 (last 30 days)
    within 60 days of the send, and was absent from their 6 months before it."""
    from core_api.mongo import get_db

    db = get_db()
    if db is None:
        return 0
    now = now or timezone.now()
    rows = (
        Delivery.objects.select_related("rec")
        .prefetch_related("rec__items")
        .filter(
            credited_at__isnull=True,
            delivered_at__isnull=False,
            rec__created_at__gte=now - timedelta(days=CREDIT_WINDOW_DAYS),
        )
    )
    credited = 0
    tops: dict[str, set[str]] = {}
    for d in rows:
        uid = str(d.recipient_id)
        try:
            if uid not in tops:
                c = _artist_counts(db, uid, now - timedelta(days=30), now)
                tops[uid] = {a for a, _ in c.most_common(20)}
            sent = [_norm(it.artist) for it in d.rec.items.all()]
            hits = [a for a in sent if a in tops[uid]]
            if not hits:
                continue
            before = _artist_counts(
                db, uid, d.rec.created_at - timedelta(days=183), d.rec.created_at
            )
            new = next((a for a in hits if before[a] == 0), None)
        except Exception:  # noqa: BLE001
            log.warning("discovery credit check failed")
            continue
        if new:
            artist = next(it.artist for it in d.rec.items.all() if _norm(it.artist) == new)
            Delivery.objects.filter(pk=d.pk).update(credit_artist=artist, credited_at=now)
            _status_changed(d)
            credited += 1
    return credited
