"""JNG-04-08 circle shared playlist: members add (credited), dedupe, who can remove, privacy."""

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from circles import services
from circles.models import CirclePlaylistItem
from social import services as social
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def client(u):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(u)}")
    return c


@pytest.fixture
def crew():
    owner, aanya, kabir = (
        UserFactory(username="owner"),
        UserFactory(username="aanya"),
        UserFactory(username="kabir"),
    )
    circle = services.create_circle(owner, "Indie night")
    token, _ = services.create_link(circle, owner)
    services.join_by_link(token, aanya)
    services.join_by_link(token, kabir)
    return circle, owner, aanya, kabir


def url(circle, item=None):
    return f"/api/v1/circles/{circle.pk}/playlist" + (f"/{item}" if item else "")


def test_members_add_songs_credited_to_whoever_added_them(crew):
    circle, owner, aanya, kabir = crew
    r = client(aanya).post(
        url(circle),
        {"title": "Kasoor", "artist": "Prateek Kuhad", "note": "for the drive"},
        format="json",
    )
    assert (
        r.status_code == 201
        and r.json()["added_by"]["username"] == "aanya"
        and r.json()["note"] == "for the drive"
    )
    client(kabir).post(url(circle), {"title": "Husn", "artist": "Anuv Jain"}, format="json")
    body = client(owner).get(url(circle)).json()
    assert [i["title"] for i in body["items"]] == ["Husn", "Kasoor"]  # newest first
    assert (
        body["items"][1]["added_by"]["username"] == "aanya"
        and "SPOTIFY" in body["items"][1]["search_links"]
    )
    assert client(owner).get(f"/api/v1/circles/{circle.pk}").json()["playlist_count"] == 2


def test_only_members_see_or_add(crew):
    circle, *_ = crew
    outsider = UserFactory(username="outsider")
    assert client(outsider).get(url(circle)).status_code == 404  # never confirms the circle exists
    assert (
        client(outsider).post(url(circle), {"title": "A", "artist": "B"}, format="json").status_code
        == 404
    )
    assert APIClient().get(url(circle)).status_code == 401


def test_same_song_from_any_app_is_added_once(crew):
    circle, owner, aanya, _ = crew
    client(aanya).post(url(circle), {"title": "Kasoor", "artist": "Prateek Kuhad"}, format="json")
    r = client(owner).post(
        url(circle), {"title": "KASOOR", "artist": "prateek kuhad"}, format="json"
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "ALREADY_IN_PLAYLIST"
    assert (
        client(owner).post(url(circle), {"title": "", "artist": "X"}, format="json").status_code
        == 400
    )


def test_adder_or_admins_remove_others_cannot(crew):
    circle, owner, aanya, kabir = crew
    item = (
        client(aanya)
        .post(url(circle), {"title": "Kasoor", "artist": "Prateek Kuhad"}, format="json")
        .json()
    )
    listed = client(kabir).get(url(circle)).json()["items"][0]
    assert listed["can_remove"] is False
    assert client(kabir).delete(url(circle, item["id"])).status_code == 403
    assert client(aanya).delete(url(circle, item["id"])).status_code == 204
    again = (
        client(aanya)
        .post(url(circle), {"title": "Kasoor", "artist": "Prateek Kuhad"}, format="json")
        .json()
    )
    assert client(owner).get(url(circle)).json()["items"][0]["can_remove"] is True
    assert client(owner).delete(url(circle, again["id"])).status_code == 204
    assert client(owner).delete(url(circle, again["id"])).status_code == 404


def test_blocked_members_additions_are_hidden(crew):
    circle, owner, aanya, kabir = crew
    client(kabir).post(url(circle), {"title": "Song", "artist": "Kabir's pick"}, format="json")
    social.block(aanya, kabir)
    assert client(aanya).get(url(circle)).json()["items"] == []
    assert len(client(owner).get(url(circle)).json()["items"]) == 1


def test_muted_accounts_cannot_add(crew):
    from moderation.services import act

    circle, owner, aanya, _ = crew
    mod = UserFactory(username="mod", is_staff=True)
    act(mod, aanya, "mute", "spam", days=1)
    r = client(aanya).post(url(circle), {"title": "A", "artist": "B"}, format="json")
    assert r.status_code == 403 and r.json()["error"]["code"] == "MUTED"


def test_songs_stay_when_the_adder_deletes_their_account(crew):
    circle, owner, aanya, _ = crew
    client(aanya).post(url(circle), {"title": "Kasoor", "artist": "Prateek Kuhad"}, format="json")
    aanya.delete()
    items = client(owner).get(url(circle)).json()["items"]
    assert items[0]["title"] == "Kasoor" and items[0]["added_by"] is None
    assert CirclePlaylistItem.objects.count() == 1
