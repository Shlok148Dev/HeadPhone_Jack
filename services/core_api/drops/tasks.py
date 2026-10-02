"""Demo mode only: personas drop a favourite at their own hour of the day (JNG-14-01 demo data)."""

from __future__ import annotations

import hashlib
import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

log = logging.getLogger(__name__)

NOTES = (
    "on repeat since morning",
    "this one hits different at night",
    "trust me, the bridge",
    "",
    "for the commute",
    "can't stop",
    "",
    "found this last week, obsessed",
)


def _h(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:8], 16)


@shared_task
def demo_drops() -> int:
    if not settings.JINGLE_DEMO:
        return 0
    from jingle_common.demo import CATALOG, PERSONAS

    from accounts.models import User

    from . import services
    from .models import Drop

    made = 0
    users = {
        u.username: u for u in User.objects.filter(username__in=[p.username for p in PERSONAS])
    }
    from jingle_common.demo import DEMO_EMAIL

    for p in PERSONAS:
        u = users.get(p.username)
        # The demo login is a person using Jingle: it never drops automatically.
        if u is None or u.email == DEMO_EMAIL:
            continue
        local = timezone.now().astimezone(services.tz_of(u))
        day = local.date().isoformat()
        # Each persona has a drop hour (06:00-13:00), so the morning fills in over time.
        if local.hour < 6 + _h(p.username, day) % 8:
            continue
        if Drop.objects.filter(user=u, day=local.date()).exists():
            continue
        t = CATALOG[p.favourites[_h(day, p.username, "t") % len(p.favourites)]]
        try:
            services.create(
                u, title=t.title, artist=t.artist, note=NOTES[_h(day, p.username, "n") % len(NOTES)]
            )
            made += 1
        except Exception:  # noqa: BLE001 - a race with another worker is fine
            log.info("demo drop skipped", extra={"persona": p.username})
            continue
    return made
