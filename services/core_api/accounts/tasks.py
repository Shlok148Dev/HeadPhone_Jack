"""Account deletion workflow (JNG-01-10, NFR-PRIV-03)."""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

log = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5, default_retry_delay=600)
def purge_user(self, user_id: str, force: bool = False) -> bool:
    """Hard-delete a soft-deleted account once its 30-day window has passed.

    Removes the user row (cascading privacy settings and consents), their linked_sources,
    scrobble_tokens and platform_connections rows, and their Mongo listens.
    """
    from .models import User
    from .services import purge_account

    user = User.objects.filter(pk=user_id, deleted_at__isnull=False).first()
    if user is None:
        return False
    due = user.deleted_at + timedelta(days=settings.ACCOUNT_PURGE_AFTER_DAYS)
    if not force and timezone.now() < due:
        return False
    try:
        return purge_account(user_id)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc) from exc


@shared_task
def purge_due_users() -> int:
    """Sweeper (beat, every 6 h): backstop for purge tasks lost from the queue."""
    from .models import User
    from .services import purge_account

    cutoff = timezone.now() - timedelta(days=settings.ACCOUNT_PURGE_AFTER_DAYS)
    count = 0
    for uid in User.objects.filter(deleted_at__lte=cutoff).values_list("pk", flat=True):
        try:
            count += int(purge_account(uid))
        except Exception:  # noqa: BLE001
            log.warning("purge failed; will retry next sweep")
    return count
