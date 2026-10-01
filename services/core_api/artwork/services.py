"""Artwork service: real covers from official, open APIs (docs/ux/DECISIONS.md D-ART-01…05).

Order: Apple's public iTunes Search API (no key; the MusicKit catalogue replaces it once a
developer token exists) → MusicBrainz + Cover Art Archive (open data, 1 request/second) →
generative cover in the client. Spotify images are only used for
Spotify-attributed modules and never cached here. We store URLs and extracted colours, never files.

Lookups never call the network: a miss is queued and a rate-limited worker resolves it
(the iTunes Search API asks for roughly 20 calls a minute).
"""

from __future__ import annotations

import colorsys
import io
import logging
import re
from collections.abc import Iterable
from datetime import timedelta

import httpx
from django.utils import timezone

from .models import Artwork, Kind

log = logging.getLogger(__name__)
QUEUE = "artwork:queue"
ITUNES = "https://itunes.apple.com/search"
MUSICBRAINZ = "https://musicbrainz.org/ws/2/recording"
CAA = "https://coverartarchive.org/release"
USER_AGENT = "Jingle/0.1 (social music pilot)"
RETRY_MISSING_DAYS = 30
_FEAT = re.compile(r"\s*[\(\[](feat|ft|with|from|prod)[^\)\]]*[\)\]]", re.I)
_PUNCT = re.compile(r"[^\w\s]", re.U)


def norm(s: str) -> str:
    import unicodedata

    s = "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c))
    s = _FEAT.sub("", s)
    s = s.replace("&", " and ")
    return " ".join(_PUNCT.sub(" ", s.lower()).split())


def track_key(title: str, artist: str) -> str:
    return f"{norm(artist)}|{norm(title)}"


def artist_key(name: str) -> str:
    return norm(name)


def _payload(a: Artwork | None) -> dict | None:
    if a is None or a.status != "found":
        return None
    return {"url": a.url, "url_small": a.url_small, "colors": a.colors, "source": a.source}


# ---- read side (fast, no network) ---------------------------------------------------------


def lookup_tracks(pairs: Iterable[tuple[str, str]], enqueue: bool = True) -> dict[str, dict | None]:
    """{track_key: payload|None} for (title, artist) pairs; misses are queued for resolution."""
    keys = {track_key(t, a): (t, a) for t, a in pairs if t and a}
    if not keys:
        return {}
    rows = {r.key: r for r in Artwork.objects.filter(kind=Kind.TRACK, key__in=list(keys))}
    if enqueue:
        _enqueue([("track", k, *keys[k]) for k in keys if k not in rows])
    return {k: _payload(rows.get(k)) for k in keys}


def lookup_track(title: str, artist: str) -> dict | None:
    return lookup_tracks([(title, artist)]).get(track_key(title, artist))


def lookup_artists(names: Iterable[str], enqueue: bool = True) -> dict[str, dict | None]:
    keys = {artist_key(n): n for n in names if n}
    rows = {r.key: r for r in Artwork.objects.filter(kind=Kind.ARTIST, key__in=list(keys))}
    if enqueue:
        _enqueue([("artist", k, "", keys[k]) for k in keys if k not in rows])
    return {k: _payload(rows.get(k)) for k in keys}


def _enqueue(items: list[tuple[str, str, str, str]]) -> None:
    if not items:
        return
    try:
        from core_api.redis_client import get_redis

        r = get_redis()
        r.sadd(QUEUE, *[f"{kind}\t{title}\t{artist}" for kind, _k, title, artist in items])
    except Exception:  # noqa: BLE001 - artwork is decoration; never fail a request over it
        log.debug("artwork queue unavailable")


# ---- colour ------------------------------------------------------------------------------


def _hex(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(c))) for c in rgb))


def _lum(rgb) -> float:
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _with_lightness(rgb, target_l: float):
    h, _l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    return tuple(c * 255 for c in colorsys.hls_to_rgb(h, target_l, min(s, 0.6)))


def ambient(rgb, against, need: float = 4.5, dark: bool = True):
    """Shift lightness until text `against` reads at `need`:1 on it (WCAG AA over tints)."""
    steps = [i / 100 for i in range(40, -1, -2)] if dark else [i / 100 for i in range(60, 101, 2)]
    for l_ in steps:
        c = tuple(round(x) for x in _with_lightness(rgb, l_))  # check what we'll actually emit
        if contrast(c, against) >= need:
            return c
    return (8, 8, 11) if dark else (247, 247, 250)


def extract_colors(image_bytes: bytes) -> dict:
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((48, 48))
    q = img.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: 6 * 3]
    counts = sorted(q.getcolors(), reverse=True)  # [(count, index)]
    swatches = [tuple(pal[i * 3 : i * 3 + 3]) for _n, i in counts]
    dominant = swatches[0]

    def sat(c):
        return colorsys.rgb_to_hls(*(x / 255 for x in c))[2]

    accent = max(swatches[:4], key=sat)
    return {
        "dominant": _hex(dominant),
        "accent": _hex(accent),
        # Text tokens: dark theme text #f4f4f7, light theme text #111118.
        "ambient_dark": _hex(ambient(accent, (244, 244, 247), dark=True)),
        "ambient_light": _hex(ambient(accent, (17, 17, 24), dark=False)),
    }


# ---- write side (worker, network) ----------------------------------------------------------


_VARIANTS = {
    "lofi",
    "lo",
    "fi",
    "flip",
    "remix",
    "mix",
    "sped",
    "slowed",
    "reverb",
    "karaoke",
    "instrumental",
    "cover",
    "acoustic",
    "live",
    "version",
    "edit",
    "unplugged",
    "mashup",
    "reprise",
}


def _score(result: dict, title: str, artist: str) -> float:
    """Prefer the original: title and artist overlap, minus words that mark a variant
    (lo-fi flips, remixes, sped-up, karaoke…) unless the wanted title has them too."""
    rt = norm(result.get("trackName") or result.get("collectionName") or "")
    ra = norm(result.get("artistName") or "")
    t, a = norm(title), norm(artist)
    tw, rw = set(t.split()), set(rt.split())
    ts = len(tw & rw) / max(1, len(tw))
    as_ = len(set(a.split()) & set(ra.split())) / max(1, len(set(a.split())))
    extra = rw - tw
    variant = len((extra & _VARIANTS) - tw)
    exact = 0.1 if rt == t else 0.0
    return ts * 0.6 + as_ * 0.4 + exact - 0.25 * variant - 0.02 * len(extra)


def _artist_ok(result: dict, artist: str) -> bool:
    """The same title by someone else (a tribute, a namesake) is never the cover."""
    want = set(norm(artist).split())
    # Featured credits count: "Uptown Funk (feat. Bruno Mars)" by Mark Ronson is Bruno Mars's too.
    raw = f"{result.get('artistName') or ''} {result.get('trackName') or ''}"
    got = set(_PUNCT.sub(" ", raw.lower()).split()) | set(
        norm(result.get("artistName") or "").split()
    )
    return bool(want) and len(want & got) / len(want) >= 0.5


def _itunes(term: str, entity: str, client: httpx.Client) -> list[dict]:
    out: list[dict] = []
    for country in ("IN", "US"):
        r = client.get(
            ITUNES,
            params={"term": term[:200], "entity": entity, "limit": 8, "country": country},
            timeout=8,
        )
        r.raise_for_status()
        out = r.json().get("results") or []
        if out:
            break
    return out


def _mb_get(client: httpx.Client, url: str, **kw) -> httpx.Response:
    """MusicBrainz asks for ≤ 1 request/second and answers 503 when exceeded: wait and retry."""
    import time

    for attempt in range(3):
        time.sleep(1.1)
        r = client.get(url, timeout=10, follow_redirects=True, **kw)
        if r.status_code != 503:
            return r
        time.sleep(2 * (attempt + 1))
    return r


def _cover_art_archive(
    title: str, artist: str, client: httpx.Client
) -> tuple[str, str, str] | None:
    """Find the original recording on MusicBrainz and the front cover of one of its releases.

    Strict: the artist credit and title must match after normalisation, so tributes, covers
    and lo-fi flips never win. Returns (release id, 500 px url, 250 px url)."""
    t, a = norm(title), norm(artist)
    q = f'recording:"{title}" AND artist:"{artist}"'
    r = _mb_get(client, MUSICBRAINZ, params={"query": q, "fmt": "json", "limit": 5})
    if r.status_code != 200:
        return None
    for rec in r.json().get("recordings") or []:
        credits = {
            norm(c.get("name", "")) for c in rec.get("artist-credit") or [] if isinstance(c, dict)
        }
        credits |= {
            norm(c.get("artist", {}).get("name", ""))
            for c in rec.get("artist-credit") or []
            if isinstance(c, dict)
        }
        if norm(rec.get("title", "")) != t or a not in credits:
            continue
        releases = sorted(
            rec.get("releases") or [],
            key=lambda rl: (
                rl.get("status") != "Official",
                (rl.get("release-group") or {}).get("primary-type")
                not in ("Album", "Single", "EP"),
            ),
        )
        for rl in releases[:4]:
            front = f"{CAA}/{rl['id']}/front"
            head = _mb_get(client, f"{front}-250", headers={"Range": "bytes=0-0"})
            if head.status_code in (200, 206):
                return rl["id"], f"{front}-500", f"{front}-250"
    return None


def _sized(url100: str, px: int) -> str:
    return re.sub(r"/\d+x\d+bb\.(jpg|png)$", f"/{px}x{px}bb.jpg", url100)


def resolve(kind: str, title: str, artist: str, client: httpx.Client | None = None) -> Artwork:
    """Resolve one item over the network and store it (found or missing)."""
    own = client is None
    client = client or httpx.Client(headers={"User-Agent": USER_AGENT})
    key = track_key(title, artist) if kind == Kind.TRACK else artist_key(artist)
    try:
        if kind == Kind.TRACK:
            results = _itunes(f"{artist} {title}", "song", client)
            mine = [r for r in results if _artist_ok(r, artist)]
            best = max(mine, key=lambda r: _score(r, title, artist), default=None)
            ok = best is not None and _score(best, title, artist) >= 0.55
            if not ok:
                caa = _cover_art_archive(title, artist, client)
                if caa is not None:
                    rid, big, small = caa
                    img = client.get(small, timeout=10, follow_redirects=True)
                    img.raise_for_status()
                    obj, _ = Artwork.objects.update_or_create(
                        kind=kind,
                        key=key,
                        defaults={
                            "status": "found",
                            "source": "coverartarchive",
                            "url": big,
                            "url_small": small,
                            "colors": extract_colors(img.content),
                            "source_id": rid,
                        },
                    )
                    return obj
        else:
            results = _itunes(artist, "album", client)
            a = norm(artist)
            # An artist is represented by their most popular album's cover (real artwork;
            # no third-party artist-photo source needed — D-ART-03).
            best = next((r for r in results if norm(r.get("artistName", "")) == a), None)
            ok = best is not None
            if not ok:
                # Fall back to the cover of one of their own songs we already resolved.
                mine = Artwork.objects.filter(
                    kind=Kind.TRACK, status="found", key__startswith=f"{a}|"
                ).first()
                if mine is not None:
                    obj, _ = Artwork.objects.update_or_create(
                        kind=kind,
                        key=key,
                        defaults={
                            "status": "found",
                            "source": mine.source,
                            "url": mine.url,
                            "url_small": mine.url_small,
                            "colors": mine.colors,
                            "source_id": mine.source_id,
                        },
                    )
                    return obj
        if not ok:
            obj, _ = Artwork.objects.update_or_create(
                kind=kind, key=key, defaults={"status": "missing", "source": "itunes"}
            )
            return obj
        small = best.get("artworkUrl100") or ""
        img = client.get(small, timeout=8)
        img.raise_for_status()
        obj, _ = Artwork.objects.update_or_create(
            kind=kind,
            key=key,
            defaults={
                "status": "found",
                "source": "itunes",
                "url": _sized(small, 600),
                "url_small": _sized(small, 120),
                "colors": extract_colors(img.content),
                "source_id": str(best.get("trackId") or best.get("collectionId") or ""),
            },
        )
        return obj
    finally:
        if own:
            client.close()


def drain(limit: int = 15) -> int:
    """Worker: resolve up to `limit` queued items (≈ the iTunes guidance per minute)."""
    from core_api.redis_client import get_redis

    r = get_redis()
    done = 0
    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for _ in range(limit):
            item = r.spop(QUEUE)
            if not item:
                break
            kind, title, artist = item.split("\t")
            key = track_key(title, artist) if kind == Kind.TRACK else artist_key(artist)
            stale = timezone.now() - timedelta(days=RETRY_MISSING_DAYS)
            if (
                Artwork.objects.filter(kind=kind, key=key)
                .exclude(status="missing", fetched_at__lt=stale)
                .exists()
            ):
                continue
            try:
                resolve(kind, title, artist, client)
                done += 1
            except Exception:  # noqa: BLE001
                log.warning("artwork resolve failed", extra={"kind": kind})
                r.sadd(QUEUE, item)  # try again next run
                break
    return done


def enrich(items: list[dict], title: str = "title", artist: str = "artist") -> list[dict]:
    """Add artwork_url / artwork_small / artwork_colors to song dicts in place (one query)."""
    found = lookup_tracks((i.get(title) or "", i.get(artist) or "") for i in items)
    for i in items:
        p = found.get(track_key(i.get(title) or "", i.get(artist) or ""))
        if p and not i.get("artwork_url"):
            i["artwork_url"] = p["url"]
        i.setdefault("artwork_url", None)
        i["artwork_small"] = p["url_small"] if p else None
        i["artwork_colors"] = p["colors"] if p else None
    return items


def enrich_artists(items: list[dict], name: str = "name") -> list[dict]:
    found = lookup_artists(i.get(name) or "" for i in items)
    for i in items:
        p = found.get(artist_key(i.get(name) or ""))
        i["image_url"] = p["url_small"] if p else None
        i["image_colors"] = p["colors"] if p else None
    return items
