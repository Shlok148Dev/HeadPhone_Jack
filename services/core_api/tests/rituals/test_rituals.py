"""Rituals (EP-09): battles, season, recap. Gherkin: features/ep09/JNG-09_battle_integrity.feature."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import time_machine
from pytest_bdd import given, scenarios, then, when
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.services import create_account
from circles import services as circles
from core_api.errors import ApiError
from notifications.models import Notification
from rituals import services
from rituals.models import Battle, Recap

pytestmark = pytest.mark.django_db
scenarios("../features/ep09/JNG-09_battle_integrity.feature")
IST = ZoneInfo("Asia/Kolkata")
MONDAY = date(2026, 10, 5)


def at(day: int, h: int, m: int = 0, s: int = 0) -> datetime:
    """A time in the week of MONDAY (0 = Monday) in IST."""
    d = MONDAY + timedelta(days=day)
    return datetime(d.year, d.month, d.day, h, m, s, tzinfo=IST)


def mk(name):
    return create_account(
        email=f"{name}@x.test",
        username=name,
        password="password-1234",
        display_name=name.title(),
        birth_year=1999,
    )


def client(u):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(u)}")
    return c


def crew(n=4):
    owner = mk("own")
    c = circles.create_circle(owner, "Crew")
    token, _ = circles.create_link(c, owner)
    people = [owner]
    for i in range(n - 1):
        u = mk(f"m{i}")
        circles.join_by_link(token, u)
        people.append(u)
    return c, people


def song(i):
    return {"title": f"Song {i}", "artist": f"Artist {i}"}


def battle_with_noms(c, people):
    b = services.battle_for(c, at(1, 12))
    for i, u in enumerate(people):
        services.nominate(b, u, song(i), now=at(1, 12))
    return b


# ---- Gherkin ------------------------------------------------------------------------------


@given("voting closed at 21:00 IST on Sunday", target_fixture="ctx")
def _closed():
    c, people = crew(3)
    b = battle_with_noms(c, people)
    noms = list(b.nominations.order_by("created_at"))
    services.vote(b, people[1], noms[0].pk, now=at(5, 12))
    assert b.closes_at == at(6, 21)
    return {"b": b, "voter": people[2], "nom": noms[0], "before": services.leaderboard(b)}


@when("a vote arrives at 21:00:05")
def _late(ctx):
    with pytest.raises(ApiError) as e:
        services.vote(ctx["b"], ctx["voter"], ctx["nom"].pk, now=at(6, 21, 0, 5))
    ctx["error"] = e.value


@then('it is rejected with "Voting has closed"')
def _rejected(ctx):
    assert ctx["error"].message == "Voting has closed"


@then("the leaderboard is unchanged")
def _unchanged(ctx):
    assert services.leaderboard(ctx["b"]) == ctx["before"]


# ---- rules --------------------------------------------------------------------------------


def test_phases_follow_the_circle_schedule():
    c, _ = crew(2)
    b = services.battle_for(c, at(1, 12))
    assert b.week == MONDAY
    assert services.phase(b, at(0, 17)) == "upcoming"
    assert services.phase(b, at(0, 18)) == "nominating"
    assert services.phase(b, at(4, 18)) == "voting"
    assert services.phase(b, at(6, 21)) == "closed"
    c.battle_schedule = {"nominate": "TUE 09:00", "vote": "THU 09:00", "close": "SAT 20:00"}
    c.save()
    nxt = services.battle_for(c, at(8, 10))  # next Tuesday
    assert nxt.vote_opens == at(10, 9) and nxt.closes_at == at(12, 20)


def test_JNG_09_02_one_nomination_three_votes_not_own():
    c, people = crew(5)
    b = battle_with_noms(c, people)
    services.nominate(b, people[0], song(99), now=at(2, 12))  # changing your pick is fine
    assert b.nominations.filter(user=people[0]).get().title == "Song 99"
    noms = {n.user_id: n for n in b.nominations.all()}
    voter = people[0]
    with pytest.raises(ApiError, match="own song"):
        services.vote(b, voter, noms[voter.pk].pk, now=at(5, 12))
    for u in people[1:4]:
        services.vote(b, voter, noms[u.pk].pk, now=at(5, 12))
    with pytest.raises(ApiError, match="3 votes"):
        services.vote(b, voter, noms[people[4].pk].pk, now=at(5, 12))
    services.unvote(b, voter, noms[people[1].pk].pk, now=at(5, 12))
    services.vote(b, voter, noms[people[4].pk].pk, now=at(5, 12))
    with pytest.raises(ApiError, match="Nominations are closed"):
        services.nominate(b, people[1], song(7), now=at(5, 12))
    with pytest.raises(ApiError, match="hasn't opened"):
        services.vote(
            services.battle_for(c, at(8, 12)), voter, noms[people[1].pk].pk, now=at(8, 12)
        )


def test_JNG_09_03_results_published_by_close_job_with_notifications():
    c, people = crew(3)
    b = battle_with_noms(c, people)
    noms = {n.user_id: n for n in b.nominations.all()}
    services.vote(b, people[0], noms[people[1].pk].pk, now=at(5, 12))
    services.vote(b, people[2], noms[people[1].pk].pk, now=at(5, 12))
    services.vote(b, people[1], noms[people[2].pk].pk, now=at(5, 12))
    assert services.close_due(at(6, 20, 59)) == 0
    assert services.close_due(at(6, 21, 1)) == 1  # well inside 5 minutes
    b.refresh_from_db()
    assert [(r["user"]["username"], r["rank"], r["votes"]) for r in b.results] == [
        ("m0", 1, 2),
        ("m1", 2, 1),
        ("own", 3, 0),
    ]
    assert Notification.objects.filter(type="battle").count() == 3
    assert services.close_due(at(6, 21, 2)) == 0  # idempotent


def test_battle_api_hides_names_while_voting_and_reveals_after():
    c, people = crew(3)
    b = battle_with_noms(c, people)
    with time_machine.travel(at(5, 12), tick=False):
        body = client(people[0]).get(f"/api/v1/circles/{c.pk}/battle").json()
        assert body["phase"] == "voting" and body["votes_left"] == 3
        assert all("user" not in n for n in body["nominations"])
        target = next(n for n in body["nominations"] if not n["mine"])
        r = client(people[0]).post(
            f"/api/v1/battles/{b.pk}/votes", {"nomination_id": target["id"]}, format="json"
        )
        assert r.json()["votes_left"] == 2
        assert client(mk("xx")).get(f"/api/v1/circles/{c.pk}/battle").status_code == 404
    with time_machine.travel(at(6, 21, 2), tick=False):
        services.close_due()
        body = client(people[0]).get(f"/api/v1/circles/{c.pk}/battle").json()
        assert body["phase"] == "closed" and body["results"][0]["user"]["username"]


def test_JNG_09_08_skip_week_and_JNG_09_04_season_ignores_it():
    c, people = crew(3)
    owner = people[0]
    m = c.members.get(user=owner)
    # Week 1 runs; m0 wins.
    b1 = battle_with_noms(c, people)
    noms = {n.user_id: n for n in b1.nominations.all()}
    services.vote(b1, owner, noms[people[1].pk].pk, now=at(5, 12))
    services.close_due(at(6, 22))
    # Week 2 is skipped by an admin.
    b2 = services.skip_week(c, m, at(8, 12))
    assert services.phase(b2) == "skipped"
    with pytest.raises(ApiError):
        services.skip_week(c, c.members.get(user=people[1]), at(8, 12))  # members can't
    services.close_due(at(13, 22))
    season = services.season(c)
    assert season["weeks"] == 1 and season["table"][0]["user"]["username"] == "m0"
    assert season["table"][0]["wins"] == 1


def test_JNG_09_05_recap_and_JNG_09_06_explicit_share(mongo_db):
    u = mk("aanya")
    sept = datetime(2026, 9, 10, 12, tzinfo=IST)
    mongo_db.listens.insert_many(
        [
            {
                "meta": {"user_id": str(u.pk)},
                "played_at": sept + timedelta(minutes=i),
                "raw": {"artist": "Arijit Singh", "title": "Kesariya", "duration_ms": 240_000},
            }
            for i in range(10)
        ]
        + [
            {
                "meta": {"user_id": str(u.pk)},
                "played_at": sept,
                "raw": {"artist": "Hidden", "title": "x"},
                "analytics_allowed": False,
            }
        ]
    )
    with time_machine.travel(datetime(2026, 10, 1, 6, tzinfo=IST), tick=False):
        assert services.make_recaps() == 1
        assert services.make_recaps() == 0  # once per month
    r = Recap.objects.get(user=u)
    assert r.month == "2026-09" and r.data["minutes"] == 40 and r.data["plays"] == 10
    assert r.data["top_tracks"][0]["title"] == "Kesariya"
    assert all(a["name"] != "Hidden" for a in r.data["top_artists"])
    assert Notification.objects.filter(user=u, type="recap").exists()
    c = client(u)
    assert c.get("/api/v1/recaps").json()[0]["share_url"] is None
    url = c.post(f"/api/v1/recaps/{r.pk}/share").json()["share_url"]
    token = url.rsplit("/", 1)[1]
    shared = APIClient().get(f"/api/v1/recaps/shared/{token}").json()
    assert shared["name"] == "Aanya" and shared["data"]["plays"] == 10
    c.delete(f"/api/v1/recaps/{r.pk}/share")
    assert APIClient().get(f"/api/v1/recaps/shared/{token}").status_code == 404


def test_rituals_overview_lists_each_circle():
    c, people = crew(2)
    body = client(people[0]).get("/api/v1/rituals").json()
    assert [b["circle"]["name"] for b in body["battles"]] == ["Crew"]
    assert body["recap"] is None
    assert Battle.objects.count() == 1
