"""ADR-0010: the demo simulator behaves like the Companion and keeps the honest gaps."""
# ruff: noqa: S311

import random

from jingle_common.demo import PERSONAS, Persona, demo_token
from jingle_common.enums import Platform

from ingest_ml.auth import well_formed
from ingest_ml.demo.simulator import HEARTBEAT_S, PersonaSim, backfill


def _persona(platform: Platform, web_share: float) -> Persona:
    return Persona("t", "T", platform, web_share, (0,))


def _run(sim: PersonaSim, seconds: int) -> list[dict]:
    out: list[dict] = []
    for t in range(0, seconds, 5):
        out.extend(sim.step(1_000_000.0 + t))
    return out


def test_web_session_heartbeats_then_scrobbles_once() -> None:
    sim = PersonaSim(_persona(Platform.YOUTUBE_MUSIC, 1.0), random.Random(1))
    import ingest_ml.demo.simulator as mod

    mod.START_PROBABILITY, old = 1.0, mod.START_PROBABILITY
    try:
        subs = _run(sim, 268 + 10)
    finally:
        mod.START_PROBABILITY = old
    kinds = [s["listen_type"] for s in subs]
    assert kinds.count("single") == 1
    # a heartbeat at least every 30 s while playing keeps Live fresh (< 90 s)
    assert kinds.count("playing_now") >= 268 // HEARTBEAT_S
    info = subs[0]["payload"][0]["track_metadata"]["additional_info"]
    assert info["music_service"] == "music.youtube.com"


def test_phone_only_amazon_never_goes_live_or_scrobbles() -> None:
    import ingest_ml.demo.simulator as mod

    sim = PersonaSim(_persona(Platform.AMAZON_MUSIC, 0.0), random.Random(2))
    mod.START_PROBABILITY, old = 1.0, mod.START_PROBABILITY
    try:
        assert _run(sim, 3600) == []
    finally:
        mod.START_PROBABILITY = old
    assert backfill(_persona(Platform.AMAZON_MUSIC, 0.0), random.Random(3), 1e9) is None


def test_spotify_phone_play_arrives_as_recent_only() -> None:
    import ingest_ml.demo.simulator as mod

    sim = PersonaSim(_persona(Platform.SPOTIFY, 0.0), random.Random(4))
    mod.START_PROBABILITY, old = 1.0, mod.START_PROBABILITY
    try:
        subs = _run(sim, 480)
    finally:
        mod.START_PROBABILITY = old
    kinds = {s["listen_type"] for s in subs}
    assert kinds == {"single"}  # never playing_now: phone listening is never Live


def test_demo_tokens_are_well_formed_and_distinct() -> None:
    toks = {demo_token(p.username, "k" * 40) for p in PERSONAS}
    assert len(toks) == len(PERSONAS)
    assert all(well_formed(t) for t in toks)
