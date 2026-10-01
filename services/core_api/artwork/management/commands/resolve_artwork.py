"""Resolve queued artwork now, paced for the iTunes Search API (~20 calls a minute).

python manage.py resolve_artwork            # drain the queue
python manage.py resolve_artwork --demo     # queue + resolve the whole demo catalogue first
"""

import time

from django.core.management.base import BaseCommand

from artwork import services


class Command(BaseCommand):
    help = "Resolve real artwork for queued tracks and artists."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="queue the demo catalogue first")
        parser.add_argument("--pace", type=float, default=3.2, help="seconds between API calls")

    def handle(self, *args, demo=False, pace=3.2, **opts):
        if demo:
            queue_demo_catalogue()
        total = 0
        while True:
            n = services.drain(limit=1)
            if not n:
                from core_api.redis_client import get_redis

                if not get_redis().scard(services.QUEUE):
                    break
                continue  # item was already resolved or retried
            total += n
            if total % 10 == 0:
                self.stdout.write(f"resolved {total}")
            time.sleep(pace)
        self.stdout.write(f"done: {total} resolved")


def queue_demo_catalogue() -> None:
    from jingle_common.demo import CATALOG

    services.lookup_tracks([(t.title, t.artist) for t in CATALOG])
    services.lookup_artists({t.artist for t in CATALOG})
