"""Suggested circles via Leiden (Technical Bible 5.5; JNG-04-05). Suggestions only: nobody is
ever added without accepting an invite (BR-08).

1. Weighted graph over accepted friendships, edge weight 0.5 + cos(taste).
2. Leiden (igraph + leidenalg, resolution 1.0).
3. Keep communities of 3–12 with mean internal edge weight ≥ 0.9 that don't already match a
   circle (Jaccard < 0.6).
4. Name from the strongest shared genre/artist ("Your indie crew"); editable by the user.
5. Suggest to the member with the most internal edges; skip if dismissed in the last 30 days.
"""

from __future__ import annotations

from collections import Counter

import numpy as np

MIN_SIZE, MAX_SIZE = 3, 12
MIN_MEAN_WEIGHT = 0.9
MAX_JACCARD = 0.6


def _cos(a, b) -> float:
    if a is None or b is None:
        return 0.0
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    return 0.0 if na == 0 or nb == 0 else float(np.dot(a, b) / (na * nb))


def communities(
    friends: dict[str, set[str]], vectors: dict[str, np.ndarray], seed: int = 7
) -> list[list[str]]:
    import igraph as ig
    import leidenalg

    nodes = sorted(u for u, fs in friends.items() if fs)
    if len(nodes) < MIN_SIZE:
        return []
    index = {u: i for i, u in enumerate(nodes)}
    edges, weights = [], []
    for u in nodes:
        for v in friends[u]:
            if v in index and u < v:
                edges.append((index[u], index[v]))
                weights.append(0.5 + _cos(vectors.get(u), vectors.get(v)))
    g = ig.Graph(n=len(nodes), edges=edges)
    g.es["weight"] = weights
    part = leidenalg.find_partition(
        g,
        leidenalg.RBConfigurationVertexPartition,
        weights="weight",
        resolution_parameter=1.0,
        seed=seed,
    )
    out = []
    for members in part:
        ids = [nodes[i] for i in members]
        if not MIN_SIZE <= len(ids) <= MAX_SIZE:
            continue
        sub = g.subgraph(members)
        if sub.ecount() == 0 or float(np.mean(sub.es["weight"])) < MIN_MEAN_WEIGHT:
            continue
        out.append(sorted(ids))
    return out


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def pick_owner(members: list[str], friends: dict[str, set[str]]) -> str:
    s = set(members)
    return max(members, key=lambda u: (len(friends.get(u, set()) & s), u))


def name_for(
    members: list[str], seeds: dict[str, dict[str, list[str]]], tops: dict[str, list[str]]
) -> str:
    genres = Counter(g for u in members for g in seeds.get(u, {}).get("genres", []))
    if genres:
        g, n = genres.most_common(1)[0]
        if n >= 2:
            return f"Your {g.lower()} crew"
    artists = Counter(a for u in members for a in tops.get(u, [])[:5])
    if artists:
        a, n = artists.most_common(1)[0]
        if n >= 2:
            return f"The {a} fans"
    return "Your crew"


def suggestions(
    friends: dict[str, set[str]],
    vectors: dict[str, np.ndarray],
    existing: list[set[str]],
    seeds: dict[str, dict[str, list[str]]],
    tops: dict[str, list[str]],
) -> list[tuple[str, list[str], str]]:
    """Return (owner_to_suggest_to, members, name) for each qualifying community."""
    out = []
    for members in communities(friends, vectors):
        s = set(members)
        if any(jaccard(s, e) >= MAX_JACCARD for e in existing):
            continue
        out.append((pick_owner(members, friends), members, name_for(members, seeds, tops)))
    return out
