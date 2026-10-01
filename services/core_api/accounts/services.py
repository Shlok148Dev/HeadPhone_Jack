"""Account workflows shared by views and tasks (JNG-01-01, JNG-01-10, JNG-13-04)."""

from __future__ import annotations

import logging
import re
import secrets
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from core_api import events

from .models import (
    CONSENT_DESCRIPTIONS,
    REQUIRED_PURPOSES,
    Consent,
    ConsentPurpose,
    PrivacySettings,
    User,
)
from .validators import RESERVED_USERNAMES, contains_profanity

log = logging.getLogger(__name__)


# ---------------------------------------------------------------- sign-up


@transaction.atomic
def create_account(
    *,
    email: str,
    username: str,
    password: str | None,
    display_name: str = "",
    birth_year: int | None = None,
    google_sub: str | None = None,
) -> User:
    """Create a user with default privacy settings and the ``core_service`` consent."""
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        display_name=display_name or username,
        birth_year=birth_year,
        google_sub=google_sub,
    )
    if password is None:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    PrivacySettings.objects.create(user=user)
    give_consent(user, ConsentPurpose.CORE_SERVICE)
    return user


def username_taken(username: str, exclude_id=None) -> bool:
    qs = User.objects.filter(username__iexact=username)
    if exclude_id is not None:
        qs = qs.exclude(pk=exclude_id)
    return qs.exists()


def derive_username(email: str) -> str:
    """Auto-derive an editable username for Google sign-ups (JNG-12-07 rules apply)."""
    local = email.split("@", 1)[0].lower()
    base = re.sub(r"[^a-z0-9_.]", "", local)[:14].strip(".")
    if len(base) < 3 or base in RESERVED_USERNAMES or contains_profanity(base):
        base = "listener"
    candidate = base
    for _ in range(20):
        if not username_taken(candidate):
            return candidate
        candidate = f"{base}{secrets.randbelow(900000) + 100000}"[:20]
    return f"user{secrets.token_hex(6)}"  # pragma: no cover - vanishingly unlikely


# ---------------------------------------------------------------- tokens


def issue_tokens(user: User) -> tuple[str, str]:
    """Return (access, refresh). Claims: sub=user UUID, typ, iss=jingle-core (CONTRACTS.md §3)."""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def set_refresh_cookie(response, refresh: str) -> None:
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite="Lax",
        path=settings.REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(
        settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH, samesite="Lax"
    )


def revoke_all_tokens(user: User) -> int:
    """Blacklist every outstanding refresh token of the user."""
    count = 0
    for tok in OutstandingToken.objects.filter(user=user):
        _, created = BlacklistedToken.objects.get_or_create(token=tok)
        count += int(created)
    return count


# ---------------------------------------------------------------- consents


def active_consent(user: User, purpose: str) -> Consent | None:
    return Consent.objects.filter(user=user, purpose=purpose, withdrawn_at__isnull=True).first()


def give_consent(user: User, purpose: str) -> Consent:
    existing = active_consent(user, purpose)
    if existing is not None:
        return existing
    try:
        with transaction.atomic():
            consent = Consent.objects.create(
                user=user, purpose=purpose, version=settings.CONSENT_VERSION
            )
    except IntegrityError:  # concurrent grant
        return active_consent(user, purpose)
    _apply_consent_side_effects(user, purpose, given=True)
    return consent


def withdraw_consent(user: User, purpose: str) -> None:
    updated = Consent.objects.filter(user=user, purpose=purpose, withdrawn_at__isnull=True).update(
        withdrawn_at=timezone.now()
    )
    if updated:
        _apply_consent_side_effects(user, purpose, given=False)


def _apply_consent_side_effects(user: User, purpose: str, *, given: bool) -> None:
    if purpose == ConsentPurpose.LASTFM_LINK and not given:
        from sources.connect_views import remove_route

        uid = user.pk
        transaction.on_commit(lambda: remove_route(uid, "LASTFM"))
    if purpose == ConsentPurpose.ACTIVITY_SHARING and not given:
        # Withdrawal = stop collecting and erase collected listening data (DPDP s.6(6)).
        from sources.views import delete_ingest_data

        uid = user.pk
        transaction.on_commit(lambda: delete_ingest_data(uid))
    if purpose == ConsentPurpose.SUGGESTIONS_DISCOVERABILITY and user.discoverable != given:
        user.discoverable = given
        user.save(update_fields=["discoverable", "updated_at"])


def consent_summary(user: User) -> list[dict]:
    """One item per purpose, in declaration order, with the current state."""
    rows = list(Consent.objects.filter(user=user).order_by("-given_at"))
    latest: dict[str, Consent] = {}
    for row in rows:
        latest.setdefault(row.purpose, row)
    items = []
    for purpose in ConsentPurpose:
        row = latest.get(purpose.value)
        items.append(
            {
                "purpose": purpose.value,
                "description": CONSENT_DESCRIPTIONS[purpose],
                "required": purpose in REQUIRED_PURPOSES,
                "given": bool(row and row.withdrawn_at is None),
                "version": row.version if row else None,
                "given_at": row.given_at if row else None,
                "withdrawn_at": row.withdrawn_at if row else None,
            }
        )
    return items


# ---------------------------------------------------------------- private mode

PRIVATE_FOREVER = datetime(9999, 12, 31, tzinfo=UTC)
PRIVATE_DURATIONS = {"1h": timedelta(hours=1), "8h": timedelta(hours=8)}


def set_private_mode(user: User, choice: str, now=None) -> None:
    """JNG-02-06: ``1h`` | ``8h`` | ``until_off`` | ``off``."""
    now = now or timezone.now()
    if choice == "off":
        user.private_until = None
    elif choice == "until_off":
        user.private_until = PRIVATE_FOREVER
    else:
        user.private_until = now + PRIVATE_DURATIONS[choice]
    user.save(update_fields=["private_until", "updated_at"])


def private_mode_state(user: User, now=None) -> dict:
    now = now or timezone.now()
    until = user.private_until
    active = bool(until and until > now)
    indefinite = bool(active and until.year >= 9999)
    return {"active": active, "until": until if active and not indefinite else None}


# ---------------------------------------------------------------- deletion


def live_state_keys(user_id) -> list[str]:
    return [f"np:{user_id}", f"last:{user_id}", f"presence:{user_id}", f"sug:{user_id}"]


def delete_spotify_direct_data(user_id) -> None:
    """BR-03 / ADR-0007: direct-Spotify API data goes immediately, not after 30 days."""
    from core_api.mongo import get_db
    from sources.models import LinkedSource, SourceKind

    LinkedSource.objects.filter(user_id=user_id, kind=SourceKind.SPOTIFY).delete()
    db = get_db()
    if db is not None:
        try:
            db.listens.delete_many(
                {
                    "$or": [
                        {"user_id": str(user_id), "via": "DIRECT", "platform": "SPOTIFY"},
                        {
                            "meta.user_id": str(user_id),
                            "meta.via": "DIRECT",
                            "meta.platform": "SPOTIFY",
                        },
                    ]
                }
            )
        except Exception:  # noqa: BLE001
            log.warning("mongo spotify-direct delete failed; hourly sweeper will retry")


def soft_delete_account(user: User) -> None:
    """JNG-01-10 step 1: hide and anonymise now; ``purge_user`` removes the rest after 30 days."""
    from core_api.redis_client import get_redis

    now = timezone.now()
    uid = user.pk
    with transaction.atomic():
        user.deleted_at = now
        user.is_active = False
        user.email = f"deleted-{uid.hex}@deleted.invalid"
        user.username = f"del_{uid.hex[:16]}"
        user.display_name = ""
        user.college = ""
        user.city = ""
        user.birth_year = None
        user.discoverable = False
        user.google_sub = None
        user.private_until = None
        user.first_name = ""
        user.last_name = ""
        user.set_unusable_password()
        user.save()
        Consent.objects.filter(user=user, withdrawn_at__isnull=True).update(withdrawn_at=now)
        revoke_all_tokens(user)
        delete_spotify_direct_data(uid)
    try:
        get_redis().delete(*live_state_keys(uid))
    except Exception:  # noqa: BLE001
        log.warning("redis live-state delete failed")
    from sources.views import delete_ingest_data

    transaction.on_commit(lambda: delete_ingest_data(uid))  # purge_account retries if this fails
    events.publish_domain("feed.invalidate", {"user_id": str(uid), "reason": "account_deleted"})

    def _enqueue():
        from .tasks import purge_user

        try:
            purge_user.apply_async(
                args=[str(uid)], countdown=settings.ACCOUNT_PURGE_AFTER_DAYS * 86400
            )
        except Exception:  # noqa: BLE001
            log.warning("purge enqueue failed; purge_due_users sweeper is the backstop")

    transaction.on_commit(_enqueue)


def purge_account(user_id) -> bool:
    """Hard-delete a soft-deleted user and every row and listen tied to them."""
    from core_api.mongo import get_db
    from sources.models import LinkedSource, PlatformConnection, ScrobbleToken

    user = User.objects.filter(pk=user_id, deleted_at__isnull=False).first()
    if user is None:
        return False
    from sources.views import delete_ingest_data

    if not delete_ingest_data(user_id):
        raise RuntimeError("ingest-ml data deletion failed; purge will retry")
    LinkedSource.objects.filter(user_id=user_id).delete()
    ScrobbleToken.objects.filter(user_id=user_id).delete()
    PlatformConnection.objects.filter(user_id=user_id).delete()
    db = get_db()
    if db is not None:
        try:
            db.listens.delete_many(
                {"$or": [{"user_id": str(user_id)}, {"meta.user_id": str(user_id)}]}
            )
        except Exception:  # noqa: BLE001
            log.warning("mongo listens purge failed")
            raise
    user.delete()
    return True


# ---------------------------------------------------------------- export


def export_account(user: User) -> dict:
    """JNG-13-04 / NFR-PRIV-06. Extend as new domains ship."""
    from sources.models import PlatformConnection, ScrobbleToken

    privacy = PrivacySettings.for_user(user)
    return {
        "exported_at": timezone.now(),
        "profile": {
            "id": str(user.pk),
            "email": user.email,
            "username": user.username,
            "display_name": user.display_name,
            "birth_year": user.birth_year,
            "college": user.college,
            "city": user.city,
            "discoverable": user.discoverable,
            "created_at": user.created_at,
        },
        "privacy": {
            "activity_visibility": privacy.activity_visibility,
            "show_last_active": privacy.show_last_active,
            "concerts_visible": privacy.concerts_visible,
            "private_until": user.private_until,
        },
        "consents": [
            {
                "purpose": c.purpose,
                "version": c.version,
                "given_at": c.given_at,
                "withdrawn_at": c.withdrawn_at,
            }
            for c in Consent.objects.filter(user=user).order_by("given_at")
        ],
        "connections": [
            {
                "platform": c.platform,
                "status": c.status,
                "first_play_at": c.first_play_at,
                "last_signal_at": c.last_signal_at,
                "created_at": c.created_at,
            }
            for c in PlatformConnection.objects.filter(user=user).order_by("created_at")
        ],
        "companion_tokens": [
            {
                "label": t.label,
                "created_at": t.created_at,
                "last_used_at": t.last_used_at,
                "revoked_at": t.revoked_at,
            }
            for t in ScrobbleToken.objects.filter(user=user).order_by("created_at")
        ],
    }
