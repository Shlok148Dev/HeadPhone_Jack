"""Friend suggestions (Technical Bible §5; JNG-03-01…08). Pure functions over plain data so the
rules can be tested exactly; the Celery task loads the data and caches the output.

Pipeline: generate candidates → hard filters → score → diversify → explain.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

MAX_RESULTS = 20
MAX_TASTE_TWINS = 8  # zero-mutual suggestions in the final 20 (Tech Bible 5.1 step 4)
FOF_LIMIT = 500
TASTE_LIMIT = 200
MMR_LAMBDA = 0.75
W_MUTUAL, W_TASTE, W_CTX, W_CONTACT, W_LOCAL = 0.35, 0.30, 0.15, 0.10, 0.10


@dataclass(frozen=True)
class Person:
    id: str
    discoverable: bool
    adult: bool
    active: bool = True
    college: str = ""
    city: str = ""
    # Private mode on, or activity visible to nobody: reasons may use public profile data only.
    private: bool = False


@dataclass
class Graph:
    people: dict[str, Person]
    friends: dict[str, set[str]]
    pending: set[frozenset[str]] = field(default_factory=set)
    blocked: set[frozenset[str]] = field(default_factory=set)
    dismissed: dict[str, set[str]] = field(default_factory=dict)  # within the last 90 days
    # Shared context (circles, sessions, battles, concerts); empty until those features ship.
    context: dict[frozenset[str], float] = field(default_factory=dict)
    display: dict[str, str] = field(default_factory=dict)  # id → display name (for reasons)


@dataclass
class Suggestion:
    user_id: str
    score: float
    reasons: list[str]
    source_signals: list[str]
    mutuals: int


def cosine(a: np.ndarray | None, b: np.ndarray | None) -> float:
    if a is None or b is None:
        return 0.0
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    return 0.0 if na == 0 or nb == 0 else float(np.dot(a, b) / (na * nb))


def adamic_adar(g: Graph, u: str, v: str) -> tuple[float, list[str]]:
    mutual = sorted(g.friends.get(u, set()) & g.friends.get(v, set()))
    score = 0.0
    for w in mutual:
        deg = len(g.friends.get(w, set()))
        score += 1.0 / math.log(deg) if deg > 1 else 0.0
    return score, mutual


def allowed(g: Graph, u: str, v: str) -> bool:
    """Hard filters (Tech Bible 5.1 step 2). Applied before scoring and again at read time."""
    if u == v:
        return False
    pu, pv = g.people.get(u), g.people.get(v)
    if pu is None or pv is None or not pv.active or not pv.discoverable:
        return False
    if pu.adult != pv.adult:  # never suggest across the adult/minor line (SRS JNG-03 scenario)
        return False
    pair = frozenset((u, v))
    if pair in g.blocked or pair in g.pending or v in g.friends.get(u, set()):
        return False
    return v not in g.dismissed.get(u, set())


def local_signal(pu: Person, pv: Person) -> float:
    if pu.college and pu.college.casefold() == pv.college.casefold():
        return 1.0
    if pu.city and pu.city.casefold() == pv.city.casefold():
        return 0.5
    return 0.0


def candidates(g: Graph, u: str, vectors: dict[str, np.ndarray]) -> set[str]:
    """Friends of friends, taste neighbours, shared context, same college or city."""
    out: set[str] = set()
    for f in g.friends.get(u, set()):
        out |= g.friends.get(f, set())
        if len(out) >= FOF_LIMIT:
            break
    vu = vectors.get(u)
    if vu is not None:
        sims = sorted(((cosine(vu, vec), v) for v, vec in vectors.items() if v != u), reverse=True)
        out |= {v for s, v in sims[:TASTE_LIMIT] if s > 0.2}
    out |= {next(iter(p - {u})) for p in g.context if u in p}
    pu = g.people.get(u)
    if pu and (pu.college or pu.city):
        out |= {p.id for p in g.people.values() if p.id != u and local_signal(pu, p) > 0}
    out.discard(u)
    return out


def _mmr(scored: list[Suggestion], vectors: dict[str, np.ndarray], k: int) -> list[Suggestion]:
    """Maximal-marginal-relevance re-rank so the list isn't twenty people from one cluster."""
    chosen: list[Suggestion] = []
    pool = sorted(scored, key=lambda s: -s.score)
    twins = 0
    while pool and len(chosen) < k:

        def value(s: Suggestion) -> float:
            sim = max(
                (cosine(vectors.get(s.user_id), vectors.get(c.user_id)) for c in chosen),
                default=0.0,
            )
            return MMR_LAMBDA * s.score - (1 - MMR_LAMBDA) * sim

        best = max(pool, key=value)
        pool.remove(best)
        if best.mutuals == 0 and "taste" in best.source_signals:
            if twins >= MAX_TASTE_TWINS:
                continue
            twins += 1
        chosen.append(best)
    return chosen


def explain(
    g: Graph, u: str, v: str, mutual: list[str], shared_artists: list[str], local: float
) -> list[str]:
    """≤ 3 reasons from facts the viewer may see; never listening data of private users."""
    reasons: list[str] = []
    if mutual:
        if len(mutual) == 1:
            reasons.append(f"Friends with {g.display.get(mutual[0], 'a friend of yours')}")
        else:
            reasons.append(f"{len(mutual)} mutual friends")
    pv = g.people[v]
    if shared_artists and not pv.private:
        reasons.append("Both love " + " and ".join(shared_artists[:2]))
    pu = g.people[u]
    if local >= 1.0:
        reasons.append(f"Also at {pv.college}")
    elif local >= 0.5 and pu.city:
        reasons.append(f"Also in {pv.city}")
    if g.context.get(frozenset((u, v)), 0) > 0:
        reasons.append("You've been in the same circle or session")
    return reasons[:3]


def suggest_for(
    g: Graph,
    u: str,
    vectors: dict[str, np.ndarray],
    top_artists: dict[str, list[str]],
    k: int = MAX_RESULTS,
) -> list[Suggestion]:
    scored: list[Suggestion] = []
    pu = g.people.get(u)
    if pu is None or not pu.active:
        return []
    mine = set(top_artists.get(u, []))
    for v in candidates(g, u, vectors):
        if not allowed(g, u, v):
            continue
        aa, mutual = adamic_adar(g, u, v)
        cos = cosine(vectors.get(u), vectors.get(v))
        ctx = min(1.0, g.context.get(frozenset((u, v)), 0.0))
        local = local_signal(pu, g.people[v])
        score = (
            W_MUTUAL * (1 - math.exp(-aa / 2))
            + W_TASTE * max(0.0, (cos - 0.2) / 0.8)
            + W_CTX * ctx
            + W_LOCAL * local
        )
        if score <= 0:
            continue
        shared = [a for a in top_artists.get(v, []) if a in mine]
        reasons = explain(g, u, v, mutual, shared, local)
        if not reasons:  # no unexplained suggestions (JNG-03-01)
            continue
        signals = [
            s
            for s, on in (
                ("mutual", mutual),
                ("taste", cos > 0.2),
                ("context", ctx),
                ("local", local),
            )
            if on
        ]
        scored.append(Suggestion(v, round(min(1.0, score), 4), reasons, signals, len(mutual)))
    return _mmr(scored, vectors, k)
