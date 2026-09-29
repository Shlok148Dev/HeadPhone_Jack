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
from jingle_common.demo import DEMO_EMAIL, DEMO_PASSWORD_DEFAULT, PERSONAS, demo_token

from accounts.models import ConsentPurpose, User
from accounts.services import active_consent, create_account, give_consent
from sources.models import ScrobbleToken


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
                for purpose in (ConsentPurpose.ACTIVITY_SHARING,
                                ConsentPurpose.SUGGESTIONS_DISCOVERABILITY):
                    if active_consent(user, purpose) is None:
                        give_consent(user, purpose)
                token = demo_token(p.username, settings.SERVICE_TOKEN)
                ScrobbleToken.objects.get_or_create(
                    token_sha256=hashlib.sha256(token.encode()).hexdigest(),
                    defaults={"user": user, "label": "Demo simulator"},
                )
        self.stdout.write(f"demo world ready ({created} new users; login {DEMO_EMAIL})")
