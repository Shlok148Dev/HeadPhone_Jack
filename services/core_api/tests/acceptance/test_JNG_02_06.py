"""JNG-02-06 Private mode hides the card from friends (owner still sees it)."""

import time

import pytest
from pytest_bdd import given, scenarios, then, when
from rest_framework.test import APIClient

from feed.resolver import resolve_card
from tests.factories import UserFactory, put_signal

pytestmark = pytest.mark.django_db

scenarios("../features/ep02/JNG-02-06_private_mode.feature")


@given("Asha and Ravi are friends", target_fixture="people")
def friends(monkeypatch):
    # TODO(S3): create a real accepted friendship once the social graph ships.
    monkeypatch.setattr("core_api.policy.are_friends", lambda a, b: True)
    return {"asha": UserFactory(username="asha"), "ravi": UserFactory(username="ravi")}


@given("Asha is Live on Spotify")
def asha_live(people, fake_redis):
    asha = people["asha"]
    put_signal(
        fake_redis, "np", asha.pk, observed_at=time.time() - 5, via="LASTFM", platform="SPOTIFY"
    )
    assert resolve_card(asha, people["ravi"])["state"] == "LIVE"


@when("Asha turns on Private mode for 1 hour")
def private_on(people):
    client = APIClient()
    client.force_authenticate(people["asha"])
    r = client.patch("/api/v1/me/privacy", {"private_mode": "1h"}, format="json")
    assert r.status_code == 200 and r.json()["private_mode"]["active"] is True


@then("Ravi sees Asha's card as HIDDEN with no recording")
def ravi_sees_hidden(people):
    people["asha"].refresh_from_db()
    card = resolve_card(people["asha"], people["ravi"])
    assert card["state"] == "HIDDEN"
    assert card["recording"] is None
    assert "observed_at" not in card


@then("Asha still sees her own card as LIVE")
def asha_sees_own(people):
    client = APIClient()
    client.force_authenticate(people["asha"])
    assert client.get("/api/v1/me/card").json()["state"] == "LIVE"
