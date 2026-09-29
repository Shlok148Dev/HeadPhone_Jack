"""Demo play simulator (ADR-0010). Runs only when JINGLE_DEMO=1.

Personas "play" through the real ListenBrainz-compatible push endpoint with their demo tokens,
behaving like the Jingle Companion: ``playing_now`` at start and every 30 s while playing in a
browser, then one ``single`` when the track ends. Phone listening is simulated honestly:
Spotify phone plays arrive afterwards as Recent (no Live), and phone plays on Apple Music,
YouTube Music and Amazon Music are not captured at all (UX_SPEC §10).
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Any

import httpx
from jingle_common.demo import CATALOG, PERSONAS, WEB_PLAYER_HOSTS, Persona, Track, demo_token
from jingle_common.enums import Platform
from jingle_common.logging import configure

log = logging.getLogger("demo-simulator")

HEARTBEAT_S = 30
TICK_S = 5
START_PROBABILITY = 0.04  # per tick while idle ≈ a new track every ~2 min on average
BACKFILL_DAYS = 14
BACKFILL_PER_PERSONA = 40


@dataclass
class _Session:
    track: Track
    started: float
    on_web: bool
    last_heartbeat: float = 0.0


def _metadata(persona: Persona, track: Track, on_web: bool) -> dict[str, Any]:
    info: dict[str, Any] = {
        "duration_ms": track.duration_s * 1000,
        "submission_client": "Jingle Companion" if on_web else "Jingle demo (phone)",
    }
    if on_web:
        info["music_service"] = WEB_PLAYER_HOSTS[persona.platform]
    elif persona.platform is Platform.SPOTIFY:
        info["music_service_name"] = "Spotify"
    return {"artist_name": track.artist, "track_name": track.title, "release_name": track.album,
            "additional_info": info}


def pick_track(persona: Persona, rng: random.Random) -> Track:
    if persona.favourites and rng.random() < 0.75:
        return CATALOG[rng.choice(persona.favourites)]
    return rng.choice(CATALOG)


class PersonaSim:
    """Pure state machine: ``step`` returns the submissions to send at time ``now``."""

    def __init__(self, persona: Persona, rng: random.Random) -> None:
        self.persona = persona
        self.rng = rng
        self.session: _Session | None = None

    def phone_capturable(self) -> bool:
        return self.persona.platform is Platform.SPOTIFY

    def step(self, now: float) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        s = self.session
        if s is None:
            if self.rng.random() < START_PROBABILITY:
                on_web = self.rng.random() < self.persona.web_share
                s = self.session = _Session(pick_track(self.persona, self.rng), now, on_web)
            else:
                return out
        if now - s.started >= s.track.duration_s:
            if s.on_web or self.phone_capturable():
                out.append({"listen_type": "single", "payload": [{
                    "listened_at": int(s.started),
                    "track_metadata": _metadata(self.persona, s.track, s.on_web)}]})
            self.session = None
            return out
        if s.on_web and now - s.last_heartbeat >= HEARTBEAT_S:
            s.last_heartbeat = now
            out.append({"listen_type": "playing_now", "payload": [{
                "track_metadata": _metadata(self.persona, s.track, True)}]})
        return out


def backfill(persona: Persona, rng: random.Random, now: float) -> dict[str, Any] | None:
    """History that would already exist (browser plays, and Spotify phone plays)."""
    if persona.web_share == 0 and persona.platform is not Platform.SPOTIFY:
        return None  # a phone-only Apple/YouTube/Amazon listener has nothing captured yet
    payload = []
    for _ in range(BACKFILL_PER_PERSONA):
        track = pick_track(persona, rng)
        at = int(now - rng.uniform(600, BACKFILL_DAYS * 86400))
        payload.append({"listened_at": at, "track_metadata": _metadata(persona, track, True)})
    return {"listen_type": "import", "payload": payload}


async def _post(client: httpx.AsyncClient, token: str, body: dict[str, Any]) -> int:
    r = await client.post("/ingest/1/submit-listens", json=body,
                          headers={"Authorization": f"Token {token}"})
    return r.status_code


async def run(base_url: str, service_token: str, seed: int | None = None) -> None:
    rng = random.Random(seed)  # noqa: S311 - simulation, not security
    tokens = {p.username: demo_token(p.username, service_token) for p in PERSONAS}
    sims = [PersonaSim(p, rng) for p in PERSONAS]
    async with httpx.AsyncClient(base_url=base_url, timeout=10) as client:
        # Wait until core-api has seeded the demo tokens.
        while True:
            try:
                r = await client.get("/ingest/1/validate-token",
                                     headers={"Authorization": f"Token {tokens['demo']}"})
                if r.status_code == 200 and r.json().get("valid"):
                    break
            except httpx.HTTPError:
                pass
            log.info("waiting for the demo seed")
            await asyncio.sleep(5)
        now = time.time()
        for p in PERSONAS:
            body = backfill(p, rng, now)
            if body is not None:
                await _post(client, tokens[p.username], body)  # resends are de-duplicated
        log.info("demo backfill done; simulating plays")
        while True:
            now = time.time()
            for sim in sims:
                for body in sim.step(now):
                    try:
                        status = await _post(client, tokens[sim.persona.username], body)
                        if status >= 400:
                            log.warning("push rejected with %s", status)
                    except httpx.HTTPError:
                        log.warning("push failed")
            await asyncio.sleep(TICK_S)


def main() -> None:
    import os

    configure("demo-simulator")
    if os.environ.get("JINGLE_DEMO", "0") != "1":
        log.info("JINGLE_DEMO is not 1; simulator idle")
        while True:
            time.sleep(3600)
    asyncio.run(run(os.environ.get("SIMULATOR_TARGET", "http://ingest-ml:8001"),
                    os.environ["SERVICE_TOKEN"]))


if __name__ == "__main__":
    main()
