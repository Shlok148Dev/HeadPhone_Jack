"""Seed the demo world (ADR-0010). Idempotent; refuses to run unless JINGLE_DEMO=1.

Seeding writes ``scrobble_tokens`` rows directly, a documented exception to ADR-0006 (ingest-ml
normally mints them): the tokens are deterministic (``jingle_common.demo.demo_token``) so the
simulator can derive them without a shared file.
"""

import hashlib
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from jingle_common.demo import DEMO_EMAIL, DEMO_PASSWORD_DEFAULT, PERSONAS, demo_token

from accounts.models import ConsentPurpose, User
from accounts.services import active_consent, create_account, give_consent
from social.models import Friendship, FriendshipStatus
from sources.models import ScrobbleToken

# Demo friendships (Sprint 3): the demo login knows most personas; one request waits for it.
FRIENDS_OF_DEMO = (
    "aanya",
    "kabir",
    "meera",
    "dev",
    "riya",
    "arjun",
    "zoya",
    "ishaan",
    "tara",
    "vikram",
    "sana",
)
PENDING_TO_DEMO = ("neel",)
PERSONA_PAIRS = (
    ("aanya", "kabir"),
    ("aanya", "dev"),
    ("meera", "zoya"),
    ("dev", "ishaan"),
    ("riya", "tara"),
    ("neel", "kabir"),
    ("kiara", "aanya"),
    ("kiara", "kabir"),
    ("rohan", "dev"),
    ("rohan", "ishaan"),
)


class Command(BaseCommand):
    help = "Seed the demo world: a demo login and about 12 friends across four platforms."

    def handle(self, *args, **options):
        if not settings.JINGLE_DEMO:
            raise CommandError("seed_demo only runs with JINGLE_DEMO=1")
        password = os.environ.get("DEMO_PASSWORD") or DEMO_PASSWORD_DEFAULT
        created = 0
        with transaction.atomic():
            for p in PERSONAS:
                email = DEMO_EMAIL if p.username == "demo" else f"{p.username}@demo.jingle.local"
                user = User.objects.filter(username=p.username).first()
                if user is None:
                    user = create_account(
                        email=email,
                        username=p.username,
                        # Only the demo login can sign in; friends are data-only accounts.
                        password=password if p.username == "demo" else None,
                        display_name=p.display_name,
                        birth_year=2001,
                    )
                    user.college, user.city, user.discoverable = p.college, p.city, True
                    user.save(update_fields=["college", "city", "discoverable"])
                    created += 1
                for purpose in (
                    ConsentPurpose.ACTIVITY_SHARING,
                    ConsentPurpose.SUGGESTIONS_DISCOVERABILITY,
                ):
                    if active_consent(user, purpose) is None:
                        give_consent(user, purpose)
                token = demo_token(p.username, settings.SERVICE_TOKEN)
                ScrobbleToken.objects.get_or_create(
                    token_sha256=hashlib.sha256(token.encode()).hexdigest(),
                    defaults={"user": user, "label": "Demo simulator"},
                )
            users = {
                u.username: u
                for u in User.objects.filter(username__in=[p.username for p in PERSONAS])
            }
            pairs = [("demo", n, True) for n in FRIENDS_OF_DEMO] + [
                (a, b, True) for a, b in PERSONA_PAIRS
            ]
            pairs += [(n, "demo", False) for n in PENDING_TO_DEMO]
            for a, b, accepted in pairs:
                low, high = Friendship.ordered(users[a].pk, users[b].pk)
                Friendship.objects.get_or_create(
                    user_low_id=low,
                    user_high_id=high,
                    defaults={
                        "requested_by": users[a],
                        "status": FriendshipStatus.ACCEPTED
                        if accepted
                        else FriendshipStatus.PENDING,
                        "accepted_at": timezone.now() if accepted else None,
                    },
                )
        self._seed_circles()
        # Suggestions once the simulator has backfilled listening history (ADR-0010, Sprint 5).
        from jingle_ml.tasks import schedule_all_later

        schedule_all_later(120)
        self.stdout.write(f"demo world ready ({created} new users; login {DEMO_EMAIL})")

    def _seed_circles(self):
        """Two demo circles (Sprint 6): one the demo login owns, one it joined."""
        from circles.models import Circle, CircleMember, Role

        circles = (
            ("KJ Somaiya crew", "demo", ("aanya", "kabir", "dev", "ishaan")),
            ("Indie night", "zoya", ("demo", "meera", "neel")),
        )
        users = {
            u.username: u for u in User.objects.filter(username__in=[p.username for p in PERSONAS])
        }
        for name, owner, members in circles:
            if Circle.objects.filter(name=name, owner=users[owner]).exists():
                continue
            c = Circle.objects.create(name=name, owner=users[owner], member_count=1 + len(members))
            CircleMember.objects.create(circle=c, user=users[owner], role=Role.OWNER)
            for m in members:
                CircleMember.objects.create(circle=c, user=users[m], role=Role.MEMBER)
