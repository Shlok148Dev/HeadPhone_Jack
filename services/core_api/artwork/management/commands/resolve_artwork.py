"""Resolve queued artwork now, paced for the iTunes Search API (~20 calls a minute).

python manage.py resolve_artwork            # drain the queue
python manage.py resolve_artwork --demo     # queue + resolve the whole demo catalogue first
python manage.py resolve_artwork --demo --refresh   # forget demo results and match again
"""

import time

from django.core.management.base import BaseCommand

from artwork import services


class Command(BaseCommand):
    help = "Resolve real artwork for queued tracks and artists."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="queue the demo catalogue first")
        parser.add_argument("--refresh", action="store_true", help="re-match the demo catalogue")
        parser.add_argument("--pace", type=float, default=3.2, help="seconds between API calls")

    def handle(self, *args, demo=False, refresh=False, pace=3.2, **opts):
        if demo and refresh:
            from jingle_common.demo import CATALOG

            from artwork.models import Artwork, Kind

            Artwork.objects.filter(
                kind=Kind.TRACK, key__in=[services.track_key(t.title, t.artist) for t in CATALOG]
            ).delete()
            Artwork.objects.filter(
                kind=Kind.ARTIST, key__in={services.artist_key(t.artist) for t in CATALOG}
            ).delete()
        if demo:
            queue_demo_catalogue()
        total = self._drain(pace)
        if demo:
            # The queue is unordered: artists resolved before their songs could not use a
            # song cover as fallback. One more pass for the artists still missing.
            from artwork.models import Artwork, Kind

            Artwork.objects.filter(kind=Kind.ARTIST, status="missing").delete()
            queue_demo_catalogue()
            total += self._drain(pace)
        self.stdout.write(f"done: {total} resolved")

    def _drain(self, pace: float) -> int:
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
        return total


def queue_demo_catalogue() -> None:
    from jingle_common.demo import CATALOG

    services.lookup_tracks([(t.title, t.artist) for t in CATALOG])
    services.lookup_artists({t.artist for t in CATALOG})
