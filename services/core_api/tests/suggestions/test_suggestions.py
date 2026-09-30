"""Friend suggestions (Tech Bible §5; JNG-03-01…07). Pure pipeline + Gherkin safety + API."""

import json
import math
from collections import Counter

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.services import create_account
from jingle_ml import data, taste
from jingle_ml.suggest import MAX_TASTE_TWINS, Graph, Person, adamic_adar, suggest_for
from social import services as social
from suggestions.models import FeedbackAction, SuggestionFeedback

scenarios("../features/ep03/JNG-03_suggestion_safety.feature")


def P(uid, **kw):
    kw.setdefault("discoverable", True)
    kw.setdefault("adult", True)
    return Person(id=uid, **kw)


def graph(people, edges, **kw):
    friends = {p.id: set() for p in people}
    for a, b in edges:
        friends[a].add(b)
        friends[b].add(a)
    return Graph(
        people={p.id: p for p in people},
        friends=friends,
        display={p.id: p.id.title() for p in people},
        **kw,
    )


V = {"m": np.array([1.0, 0, 0]), "a": np.array([0.9, 0.1, 0]), "x": np.array([0, 1.0, 0])}
TOPS = {"m": ["Arijit Singh", "Prateek Kuhad"], "a": ["Prateek Kuhad", "Arijit Singh"]}


# ---- pure pipeline ------------------------------------------------------------------------


def test_adamic_adar_weights_small_hubs_more():
    g = graph([P(i) for i in "uvwhz"], [("u", "w"), ("v", "w"), ("u", "h"), ("v", "h"), ("h", "z")])
    score, mutual = adamic_adar(g, "u", "v")
    assert mutual == ["h", "w"]
    assert score == pytest.approx(1 / math.log(2) + 1 / math.log(3))


def test_friends_of_friends_scored_with_reasons_and_capped():
    g = graph(
        [P("m"), P("f1"), P("f2"), P("a")], [("m", "f1"), ("m", "f2"), ("f1", "a"), ("f2", "a")]
    )
    out = suggest_for(g, "m", V, TOPS)
    assert [s.user_id for s in out] == ["a"]
    s = out[0]
    assert 0 < s.score <= 1 and s.reasons[0] == "2 mutual friends"
    assert "Both love Prateek Kuhad and Arijit Singh" in s.reasons and len(s.reasons) <= 3
    assert "mutual" in s.source_signals and "taste" in s.source_signals


def test_taste_twins_capped_at_eight_and_no_unexplained_suggestions():
    people = [P("m")] + [P(f"t{i}") for i in range(12)] + [P("nobody")]
    vecs = {"m": np.array([1.0, 0])} | {f"t{i}": np.array([1.0, 0.01 * i]) for i in range(12)}
    vecs["nobody"] = np.array([1.0, 0])
    tops = {"m": ["Kendrick Lamar"]} | {f"t{i}": ["Kendrick Lamar"] for i in range(12)}
    out = suggest_for(graph(people, []), "m", vecs, tops)
    assert len(out) == MAX_TASTE_TWINS  # JNG-03-03 taste twins, at most 8 without mutuals
    assert "nobody" not in [s.user_id for s in out]  # similar vector but no explainable reason


def test_local_signal_reason():
    g = graph([P("m", college="KJ Somaiya"), P("c", college="kj somaiya")], [])
    out = suggest_for(g, "m", {}, {})
    assert out[0].reasons == ["Also at kj somaiya"]


def test_taste_vectors_use_seeds_and_normalise():
    docs = taste.documents(
        {"a": Counter({"Arijit Singh": 10})},
        {"b": {"artists": ["Arijit Singh"], "genres": ["Indie"]}},
    )
    vecs = taste.vectors(docs)
    assert set(vecs) == {"a", "b"}
    assert np.linalg.norm(vecs["a"]) == pytest.approx(1.0)
    assert float(np.dot(vecs["a"], vecs["b"])) > 0.3


def test_lineage_filter_is_train_only():
    """BR-03/BR-04, ADR-0007/0013: taste vectors never read direct-Spotify or Last.fm listens."""
    f = data.listen_filter("train")
    assert f["trainable"] is True
    with pytest.raises(ValueError):
        data.listen_filter("whatever")


# ---- Gherkin (JNG-03-01, JNG-03-06, minors) ------------------------------------------------


@pytest.fixture
def ctx():
    return {}


@given("Meera and Arjun share two mutual friends and the same taste", target_fixture="ctx")
def _base():
    return {
        "people": {"m": P("m"), "a": P("a"), "f1": P("f1"), "f2": P("f2")},
        "edges": [("m", "f1"), ("m", "f2"), ("f1", "a"), ("f2", "a")],
        "extra": {},
    }


@given(
    parsers.parse(
        "Meera has blocked Arjun, or Arjun turned discoverability off, or Meera dismissed Arjun 30 days ago"
    )
)
def _exclusions(ctx):
    ctx["cases"] = [
        {"blocked": {frozenset(("m", "a"))}},
        {"people": {**ctx["people"], "a": P("a", discoverable=False)}},
        {"dismissed": {"m": {"a"}}},
    ]


@when("Meera's suggestions are generated")
def _generate(ctx):
    ctx["results"] = []
    for case in ctx["cases"]:
        people = case.get("people", ctx["people"])
        g = graph(
            list(people.values()),
            ctx["edges"],
            blocked=case.get("blocked", set()),
            dismissed=case.get("dismissed", {}),
        )
        ctx["results"].append([s.user_id for s in suggest_for(g, "m", V, TOPS)])


@then("Arjun is not in the list")
def _absent(ctx):
    assert all("a" not in r for r in ctx["results"])


@given("Arjun has Private mode on", target_fixture="ctx")
def _private():
    people = [P("m"), P("f1"), P("f2"), P("a", private=True)]
    return {"g": graph(people, [("m", "f1"), ("m", "f2"), ("f1", "a"), ("f2", "a")])}


@when("Arjun appears as a suggestion for Meera")
def _appears(ctx):
    out = suggest_for(ctx["g"], "m", V, TOPS)
    assert [s.user_id for s in out] == ["a"]
    ctx["reasons"] = out[0].reasons


@then("the reasons use only public profile data and mutual-friend counts")
def _public(ctx):
    assert ctx["reasons"] == ["2 mutual friends"]


@then("no track, artist or listening time from Arjun is shown")
def _no_leak(ctx):
    text = " ".join(ctx["reasons"])
    assert "Arijit" not in text and "Prateek" not in text and "love" not in text


@given("Meera is 16 and Arjun is 24", target_fixture="ctx")
def _ages():
    people = [P("m", adult=False), P("f1"), P("a")]
    return {"g": graph(people, [("m", "f1"), ("f1", "a")])}


@when("suggestions are generated for either")
def _both(ctx):
    ctx["m"] = [s.user_id for s in suggest_for(ctx["g"], "m", V, TOPS)]
    ctx["a"] = [s.user_id for s in suggest_for(ctx["g"], "a", V, TOPS)]


@then("neither appears in the other's suggestions")
def _neither(ctx):
    assert "a" not in ctx["m"] and "m" not in ctx["a"]


# ---- API (reads cache, re-filters, dismiss, taste) -----------------------------------------


def mk(name, **kw):
    u = create_account(
        email=f"{name}@x.test",
        username=name,
        password="password-1234",
        display_name=name.title(),
        birth_year=1999,
    )
    u.discoverable = kw.get("discoverable", True)
    u.save(update_fields=["discoverable"])
    return u


def client(u):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(u)}")
    return c


@pytest.mark.django_db
def test_api_reads_cache_and_refilters(fake_redis, monkeypatch):
    sent = []
    monkeypatch.setattr("jingle_ml.tasks.schedule_recompute", lambda *ids: sent.append(ids))
    me, a, b, c, d = (mk(n) for n in ("meera", "arjun", "bina", "chand", "dia"))
    fake_redis.set(
        f"sug:{me.pk}",
        json.dumps(
            [
                {
                    "user_id": str(u.pk),
                    "score": 0.5,
                    "reasons": ["2 mutual friends"],
                    "source_signals": ["mutual"],
                }
                for u in (a, b, c, d)
            ]
        ),
    )
    social.block(me, b)  # blocked after the nightly run
    social.send_request(me, c)  # now pending
    d.discoverable = False
    d.save(update_fields=["discoverable"])
    api = client(me)
    body = api.get("/api/v1/suggestions").json()
    assert [r["user"]["username"] for r in body["results"]] == ["arjun"]
    assert body["pending"] is False and body["results"][0]["reasons"] == ["2 mutual friends"]
    assert api.post(f"/api/v1/suggestions/{a.pk}/dismiss").status_code == 204
    assert api.get("/api/v1/suggestions").json()["results"] == []  # JNG-03-05
    assert SuggestionFeedback.objects.filter(action=FeedbackAction.DISMISSED).count() == 1


@pytest.mark.django_db
def test_api_cold_start_and_taste(fake_redis, monkeypatch):
    sent = []
    monkeypatch.setattr("jingle_ml.tasks.schedule_recompute", lambda *ids: sent.append(ids))
    me = mk("newbie")
    api = client(me)
    body = api.get("/api/v1/suggestions").json()
    assert body == {"results": [], "pending": True, "cold_start": True} and sent  # JNG-03-07
    r = api.put(
        "/api/v1/me/taste",
        {"artists": ["Arijit Singh", " "], "genres": ["Indie", "Nope"]},
        format="json",
    )
    assert r.json()["artists"] == ["Arijit Singh"] and r.json()["genres"] == ["Indie"]
    assert api.get("/api/v1/me/taste").json()["genre_options"][0] == "Bollywood"


@pytest.mark.django_db(transaction=True)
def test_new_friendship_triggers_recompute(monkeypatch):
    sent = []
    monkeypatch.setattr("jingle_ml.tasks.schedule_recompute", lambda *ids: sent.append(ids))
    a, b = mk("anna"), mk("bala")
    social.accept(b, social.send_request(a, b))
    assert sent and {str(x) for x in sent[0]} == {str(a.pk), str(b.pk)}


@pytest.mark.django_db
def test_compute_end_to_end_with_database(fake_redis, monkeypatch):
    """Load graph from the DB, compute, cache (Mongo absent → seeds only)."""
    from jingle_ml import tasks
    from suggestions.models import TasteSeed

    monkeypatch.setattr("jingle_ml.data.artist_counts", lambda purpose="train", since_days=90: {})
    monkeypatch.setattr(tasks, "_upsert_qdrant", lambda v: None)
    me, f, fof, twin = mk("meera"), mk("fran"), mk("fofa"), mk("twin")
    social.accept(f, social.send_request(me, f))
    social.accept(fof, social.send_request(f, fof))
    for u in (me, twin):
        TasteSeed.objects.create(user=u, artists=["Arijit Singh", "Anuv Jain"], genres=["Indie"])
    counts = tasks.compute(None)
    assert counts["users"] == 4
    got = {i["user_id"]: i for i in json.loads(fake_redis.get(f"sug:{me.pk}"))}
    assert str(fof.pk) in got and got[str(fof.pk)]["reasons"][0] == "Friends with Fran"
    assert str(twin.pk) in got and any("Both love" in r for r in got[str(twin.pk)]["reasons"])
    assert str(f.pk) not in got  # already friends


def test_artist_counts_exclude_direct_spotify_and_lastfm(mongo_db):
    """Lineage on real documents: only trainable listens build taste (BR-03, BR-04)."""
    from django.utils import timezone

    now = timezone.now()

    def doc(user, artist, via, trainable):
        return {
            "played_at": now,
            "meta": {"user_id": user, "platform": "SPOTIFY", "via": via},
            "raw": {"artist": artist, "title": "t"},
            "trainable": trainable,
            "analytics_allowed": via != "DIRECT",
        }

    mongo_db.listens.insert_many(
        [
            doc("u1", "Arijit Singh", "COMPANION", True),
            doc("u1", "Arijit Singh", "COMPANION", True),
            doc("u1", "Taylor Swift", "DIRECT", False),
            doc("u1", "Lucky Ali", "LASTFM", False),
        ]
    )
    counts = data.artist_counts("train")
    assert counts == {"u1": Counter({"Arijit Singh": 2})}


def test_offline_eval_recall_and_safety():
    from jingle_ml.evaluate import evaluate

    people = [P(i) for i in ("a", "b", "c", "d", "e")] + [P("kid", adult=False)]
    edges = [("a", "b"), ("b", "c"), ("a", "c"), ("c", "d"), ("d", "e"), ("b", "d")]
    g = graph(people, edges, blocked={frozenset(("a", "e"))})
    m = evaluate(g, {}, {}, hide_share=0.34)
    assert m["unsafe_pairs"] == 0 and m["hidden_edges"] == 2
    assert 0.0 <= m["recall_at_20"] <= 1.0 and 0.0 <= m["coverage"] <= 1.0
