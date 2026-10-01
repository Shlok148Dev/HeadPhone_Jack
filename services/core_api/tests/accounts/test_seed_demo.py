"""ADR-0010 demo seed: idempotent, demo-only."""

import hashlib

import pytest
from django.core.management import CommandError, call_command
from jingle_common.demo import DEMO_EMAIL, PERSONAS, demo_token

from accounts.models import User
from sources.models import ScrobbleToken

pytestmark = pytest.mark.django_db


def test_refuses_without_demo_flag(settings):
    settings.JINGLE_DEMO = False
    with pytest.raises(CommandError):
        call_command("seed_demo")


def test_seeds_personas_idempotently(settings):
    settings.JINGLE_DEMO = True
    call_command("seed_demo")
    call_command("seed_demo")
    assert User.objects.count() == len(PERSONAS) + 1  # + the demo moderator (mod@jingle.local)
    assert User.objects.get(username="mod").is_staff
    assert ScrobbleToken.objects.count() == len(PERSONAS)
    demo = User.objects.get(email=DEMO_EMAIL)
    assert demo.check_password("jingle-demo-2026")
    assert not User.objects.get(username="aanya").has_usable_password()
    tok = demo_token("aanya", settings.SERVICE_TOKEN)
    assert ScrobbleToken.objects.filter(
        token_sha256=hashlib.sha256(tok.encode()).hexdigest(), user__username="aanya"
    ).exists()
