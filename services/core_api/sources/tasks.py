"""Periodic jobs that drive ingest-ml (Technical Bible 2.3, 7.4). Platform calls stay inside
ingest-ml (ADR-0006); these tasks only tell it when to work."""

import logging

import httpx
from celery import shared_task
from django.conf import settings

from core_api import flags

log = logging.getLogger(__name__)


def _post(path: str, payload: dict) -> dict:
    resp = httpx.post(
        f"{settings.INGEST_INTERNAL_URL.rstrip('/')}{path}",
        json=payload,
        headers={"X-Service-Token": settings.SERVICE_TOKEN},
        timeout=55,
    )
    resp.raise_for_status()
    return resp.json()


@shared_task(queue="poll", ignore_result=True, acks_late=False, soft_time_limit=55)
def poll_sources() -> dict:
    """Poll routes that are due (ListenBrainz, Last.fm, direct Spotify, flagged Apple Music)."""
    try:
        return _post(
            "/internal/poll/due", {"flags": {k: v["enabled"] for k, v in flags.all_flags().items()}}
        )
    except httpx.HTTPError:
        log.warning("poll run failed; next beat retries")
        return {}


@shared_task(queue="ingest", ignore_result=True, soft_time_limit=55)
def drain_identity_queue() -> dict:
    """Resolve queued unresolved recordings through MusicBrainz at its 1 req/s limit."""
    try:
        return _post("/internal/identity/drain?limit=40", {})
    except httpx.HTTPError:
        log.warning("identity drain failed; next beat retries")
        return {}
