"""Offline evaluation of friend suggestions (Technical Bible 5.6).

* Recall@20: hide 20 % of friendships (most recent first), regenerate, count how many hidden
  friends come back in the top 20 of either side. Target ≥ 0.30.
* Coverage: share of eligible users with ≥ 5 suggestions. Target ≥ 90 % at scale.
* Safety: blocked or adult–minor pairs ever suggested. Must be 0.
"""

from __future__ import annotations

import copy
import random

from jingle_ml.suggest import Graph, suggest_for


def evaluate(g: Graph, vectors, tops, hide_share: float = 0.2, seed: int = 7) -> dict[str, float]:
    edges = sorted({tuple(sorted((u, v))) for u, fs in g.friends.items() for v in fs})
    rng = random.Random(seed)  # noqa: S311 - evaluation sampling
    hidden = rng.sample(edges, k=max(1, int(len(edges) * hide_share))) if edges else []
    h = copy.deepcopy(g)
    for a, b in hidden:
        h.friends[a].discard(b)
        h.friends[b].discard(a)
    results = {u: [s.user_id for s in suggest_for(h, u, vectors, tops)] for u in h.people}
    found = sum(1 for a, b in hidden if b in results.get(a, []) or a in results.get(b, []))
    unsafe = 0
    for u, out in results.items():
        for v in out:
            pu, pv = g.people[u], g.people[v]
            if frozenset((u, v)) in g.blocked or pu.adult != pv.adult:
                unsafe += 1
    eligible = [u for u, p in g.people.items() if p.active]
    covered = sum(1 for u in eligible if len(results.get(u, [])) >= 5)
    return {
        "recall_at_20": round(found / len(hidden), 4) if hidden else 0.0,
        "coverage": round(covered / len(eligible), 4) if eligible else 0.0,
        "unsafe_pairs": float(unsafe),
        "hidden_edges": float(len(hidden)),
    }
