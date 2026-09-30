"""Taste vectors (Technical Bible 5.2): TF-IDF over each person's artists (+ onboarding picks),
reduced with TruncatedSVD to ≤ 128 dimensions when there are more features than that.

Only permitted data feeds these vectors: listens with ``trainable=True`` (no direct-Spotify API
data, no Last.fm data; BR-03, BR-04, ADR-0007/0013) plus the person's own onboarding picks.
"""

from __future__ import annotations

from collections import Counter

import numpy as np

DIMS = 128


def documents(
    artist_counts: dict[str, Counter[str]], seeds: dict[str, dict[str, list[str]]]
) -> dict[str, Counter[str]]:
    docs: dict[str, Counter[str]] = {}
    for uid in set(artist_counts) | set(seeds):
        c: Counter[str] = Counter(
            {f"artist:{a.casefold()}": n for a, n in artist_counts.get(uid, Counter()).items()}
        )
        seed = seeds.get(uid, {})
        for a in seed.get("artists", []):
            c[f"artist:{a.casefold()}"] += 3  # a stated favourite counts like a few plays
        for gname in seed.get("genres", []):
            c[f"genre:{gname.casefold()}"] += 3
        if c:
            docs[uid] = c
    return docs


def vectors(docs: dict[str, Counter[str]]) -> dict[str, np.ndarray]:
    if not docs:
        return {}
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.feature_extraction.text import TfidfTransformer

    ids = sorted(docs)
    counts = DictVectorizer().fit_transform([docs[i] for i in ids])
    tfidf = TfidfTransformer(sublinear_tf=True).fit_transform(counts)
    if tfidf.shape[1] > DIMS and len(ids) > DIMS:
        mat = TruncatedSVD(n_components=DIMS, random_state=7).fit_transform(tfidf)
    else:
        mat = tfidf.toarray()
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    mat = np.divide(mat, norms, out=np.zeros_like(mat), where=norms > 0)
    return {uid: mat[i] for i, uid in enumerate(ids)}


def top_artists(
    artist_counts: dict[str, Counter[str]], seeds: dict[str, dict[str, list[str]]], n: int = 20
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for uid in set(artist_counts) | set(seeds):
        ranked = [a for a, _ in artist_counts.get(uid, Counter()).most_common(n)]
        for a in seeds.get(uid, {}).get("artists", []):
            if a not in ranked:
                ranked.append(a)
        out[uid] = ranked[:n]
    return out
