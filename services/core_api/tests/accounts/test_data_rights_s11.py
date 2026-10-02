"""Data rights across every domain (JNG-13-04, JNG-01-10) after Sprints 3–10."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts import services
from accounts.models import User
from blends import services as blends
from blends.models import Blend
from circles import services as circles
from circles.models import Circle, CircleMember, Role
from listening import services as listening
from listening.models import ListeningSession
from sends import services as sends
from social import services as social

pytestmark = pytest.mark.django_db


def mk(name):
    return services.create_account(
        email=f"{name}@x.test",
        username=name,
        password="password-1234",
        display_name=name.title(),
        birth_year=1999,
    )


def befriend(a, b):
    social.accept(b, social.send_request(a, b))


def test_export_covers_every_domain(mongo_db):
    a, b = mk("anna"), mk("bala")
    befriend(a, b)
    circles.create_circle(a, "Crew")
    sends.send(
        a, [{"title": "Kasoor", "artist": "Prateek Kuhad"}], note="for you", user_ids=[str(b.pk)]
    )
    sends.send(b, [{"title": "Blue", "artist": "Yung Kai"}], user_ids=[str(a.pk)])
    mongo_db.listens.insert_one(
        {
            "meta": {"user_id": str(a.pk), "platform": "SPOTIFY"},
            "played_at": timezone.now(),
            "raw": {"title": "Kasoor", "artist": "Prateek Kuhad"},
        }
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(a)}")
    body = c.get("/api/v1/me/export").json()
    assert body["friends"] == ["bala"]
    assert body["circles"] == [{"name": "Crew", "role": "owner"}]
    assert body["sends"][0]["note"] == "for you" and body["sends"][0]["to"] == ["bala"]
    assert (
        body["received"][0]["from"] == "bala" and body["received"][0]["songs"][0]["title"] == "Blue"
    )
    assert body["listens"][0]["title"] == "Kasoor"
    for key in (
        "blends",
        "recaps",
        "battle_nominations",
        "notifications",
        "moderation",
        "taste_picks",
    ):
        assert key in body


def test_deleting_an_owner_hands_shared_spaces_over(mongo_db, monkeypatch):
    monkeypatch.setattr("sources.views.delete_ingest_data", lambda uid: True)
    owner, admin, member = mk("own"), mk("adm"), mk("mem")
    befriend(owner, admin)
    befriend(owner, member)
    befriend(admin, member)
    c = circles.create_circle(owner, "Crew")
    token, _ = circles.create_link(c, owner)
    circles.join_by_link(token, member)
    circles.join_by_link(token, admin)
    circles.set_role(c, owner, admin.pk, Role.ADMIN)
    solo = circles.create_circle(owner, "Just me")
    blend = blends.create(owner, user_ids=[admin.pk, member.pk])
    session = listening.start(owner, user_ids=[str(admin.pk)])
    listening.join(session, admin)

    services.soft_delete_account(owner)
    User.objects.filter(pk=owner.pk).update(deleted_at=timezone.now() - timedelta(days=31))
    assert services.purge_account(owner.pk) is True

    c.refresh_from_db()
    assert c.owner_id == admin.pk  # the admin outranks the earlier member
    assert CircleMember.objects.get(circle=c, user=admin).role == Role.OWNER
    assert not Circle.objects.filter(pk=solo.pk).exists()  # nobody else was in it
    assert Blend.objects.filter(pk=blend.pk, created_by__isnull=True).exists()
    s = ListeningSession.objects.get(pk=session.pk)
    assert s.host_id == admin.pk and s.ended_at is None
