"""Blend generation (Technical Bible 6.2; ADR-0021). Pure functions: no DB, easy to test.

1. Pool: each contributing member's top 100 tracks of the last 90 days.
2. Affinity per (member, track): play count / the member's top count if they played it, else
   0.5 × their artist affinity (stand-in for the LightFM score until S8+ models exist).
3. Group utility: mean affinity − 0.5 × standard deviation.
4. Constraints: 30 tracks; no member supplies more than 40 %; at most 2 tracks per artist;
   resolvable recordings win ties.
5. Reason: the strongest fact, as a deterministic template (Tech Bible 6.5, no rephrasing).
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

SIZE = 30
POOL_PER_MEMBER = 100
MAX_SHARE = 0.4
MAX_PER_ARTIST = 2
MIN_MEMBERS, MAX_MEMBERS = 2, 6


@dataclass(frozen=True)
class Track:
    key: str  # recording id, or "artist|title" when unresolved
    title: str
    artist: str
    recording_id: str | None = None


@dataclass
class Member:
    id: str
    name: str
    plays: Counter = field(default_factory=Counter)  # track key -> count

    def artist_counts(self, catalog: dict[str, Track]) -> Counter:
        c: Counter = Counter()
        for k, n in self.plays.items():
            if k in catalog:
                c[catalog[k].artist.lower()] += n
        return c


@dataclass
class Pick:
    track: Track
    reason: str
    contributor_ids: list[str]
    pinned: bool = False


def _names(names: list[str]) -> str:
    if len(names) <= 2:
        return " and ".join(names)
    if len(names) == 3:
        return f"{names[0]}, {names[1]} and {names[2]}"
    return f"{names[0]}, {names[1]} and {len(names) - 2} others"


def reason_for(
    track: Track, members: list[Member], artist_aff: dict[str, Counter]
) -> tuple[str, list[str]]:
    players = sorted(
        (m for m in members if m.plays.get(track.key)), key=lambda m: -m.plays[track.key]
    )
    if len(players) >= 2:
        verb = "both play" if len(players) == 2 else "all play"
        return f"{_names([m.name for m in players])} {verb} this", [m.id for m in players]
    fans = [
        m for m in members if m not in players and artist_aff[m.id].get(track.artist.lower(), 0) > 0
    ]
    if players and fans:
        return (
            f"From {players[0].name}'s top plays; {fans[0].name} plays a lot of {track.artist}",
            [players[0].id],
        )
    if players:
        return f"From {players[0].name}'s top plays", [players[0].id]
    if fans:
        return f"{_names([m.name for m in fans[:2]])} play a lot of {track.artist}", [fans[0].id]
    return "", []


def generate(
    members: list[Member],
    catalog: dict[str, Track],
    pinned: list[Pick] | None = None,
    size: int = SIZE,
) -> list[Pick]:
    pinned = list(pinned or [])
    contributing = [m for m in members if m.plays]
    if not contributing:
        return pinned[:size]
    tops = {m.id: max(m.plays.values()) for m in contributing}
    artist = {m.id: m.artist_counts(catalog) for m in contributing}
    artist_top = {m.id: max(artist[m.id].values(), default=1) for m in contributing}

    pool: set[str] = set()
    for m in contributing:
        pool.update(k for k, _ in m.plays.most_common(POOL_PER_MEMBER) if k in catalog)
    taken = {p.track.key for p in pinned}

    def affinity(m: Member, t: Track) -> float:
        n = m.plays.get(t.key, 0)
        if n:
            return n / tops[m.id]
        return 0.5 * artist[m.id].get(t.artist.lower(), 0) / artist_top[m.id]

    scored = []
    for k in pool - taken:
        t = catalog[k]
        affs = [affinity(m, t) for m in contributing]
        mean = sum(affs) / len(affs)
        std = math.sqrt(sum((a - mean) ** 2 for a in affs) / len(affs))
        best = max(range(len(contributing)), key=lambda i: affs[i])
        utility = mean - 0.5 * std + (0.01 if t.recording_id else 0.0)
        scored.append((utility, k, contributing[best].id))
    scored.sort(key=lambda x: (-x[0], x[1]))

    per_artist = Counter(p.track.artist.lower() for p in pinned)
    supplied: Counter = Counter()
    cap = max(1, math.ceil(MAX_SHARE * size)) if len(contributing) > 1 else size
    out = list(pinned)
    skipped = []
    for _utility, k, supplier in scored:
        if len(out) >= size:
            break
        t = catalog[k]
        if per_artist[t.artist.lower()] >= MAX_PER_ARTIST or supplied[supplier] >= cap:
            skipped.append((k, supplier))
            continue
        per_artist[t.artist.lower()] += 1
        supplied[supplier] += 1
        reason, who = reason_for(t, contributing, artist)
        out.append(Pick(t, reason, who))
    # A small group may not have enough variety: relax the share cap (never the artist cap).
    for k, _ in skipped:
        if len(out) >= size:
            break
        t = catalog[k]
        if per_artist[t.artist.lower()] >= MAX_PER_ARTIST:
            continue
        per_artist[t.artist.lower()] += 1
        reason, who = reason_for(t, contributing, artist)
        out.append(Pick(t, reason, who))
    return out
