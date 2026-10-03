"""String normalisation for track identity (SRS 4.4, Stack 6.1).

Two outputs per track:
- *clean* strings, case preserved, for display on the ``Recording`` row;
- a *norm key* ``"artist|title"``: casefolded, Latin diacritics removed, punctuation dropped,
  whitespace collapsed. Non-Latin scripts (Devanagari, Gurmukhi…) keep their combining marks.
"""

import re
import unicodedata
from dataclasses import dataclass

_FEAT = r"(?:feat\.?|ft\.?|featuring)"

# Noise suffixes in titles, mostly from YouTube uploads.
_TITLE_NOISE = [
    # (Official Video), (Official Music Video), (Official Audio), (Lyric Video), (Visualizer)
    re.compile(
        r"\s*[\(\[]\s*(?:official\s+)?(?:hd\s+|4k\s+)?(?:full\s+)?"
        r"(?:music\s+|lyrics?\s+|lyrical\s+)?"
        r"(?:video|audio|visuali[sz]er|song|video\s+song|mv)\s*[\)\]]",
        re.IGNORECASE,
    ),
    re.compile(r"\s*[\(\[]\s*(?:lyrics?|lyrical|with\s+lyrics|hd|hq|4k)\s*[\)\]]", re.IGNORECASE),
    # (From "Brahmastra") / (From “Brahmastra”) — common on Indian film soundtracks
    re.compile(r"\s*[\(\[]\s*from\s+[\"“'‘].*?[\"”'’]\s*[\)\]]", re.IGNORECASE),
    # - Remastered 2011 / - 2011 Remaster / (Remastered 2009) / [Remastered]
    re.compile(
        r"\s*[-–—]\s*(?:\d{4}\s+)?remaster(?:ed)?(?:\s+\d{4})?(?:\s+version)?\s*$", re.IGNORECASE
    ),
    re.compile(
        r"\s*[\(\[]\s*(?:\d{4}\s+)?remaster(?:ed)?(?:\s+\d{4})?(?:\s+version)?\s*[\)\]]",
        re.IGNORECASE,
    ),
    # any remaining [...] block
    re.compile(r"\s*\[[^\]]*\]"),
]

_FEAT_PAREN = re.compile(rf"\s*[\(\[]\s*{_FEAT}\s+(?P<who>[^\)\]]+)[\)\]]", re.IGNORECASE)
_FEAT_TAIL = re.compile(rf"\s+{_FEAT}\s+(?P<who>.+)$", re.IGNORECASE)
_TOPIC = re.compile(r"\s*-\s*topic\s*$", re.IGNORECASE)
_VEVO = re.compile(r"\s*vevo\s*$", re.IGNORECASE)
_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")
_SPLIT_CREDIT = re.compile(r"\s*(?:,|&|\band\b|\bx\b)\s*", re.IGNORECASE)
_SPACES = re.compile(r"\s+")


@dataclass(frozen=True)
class NormalisedTrack:
    title: str  # clean, case preserved
    artist: str  # clean primary credit, case preserved
    featured: tuple[str, ...]
    norm_title: str
    norm_artist: str

    @property
    def norm_key(self) -> str:
        return f"{self.norm_artist}|{self.norm_title}"


def fold(text: str) -> str:
    """Casefold, strip Latin diacritics, turn punctuation/symbols into spaces, collapse spaces."""
    text = unicodedata.normalize("NFKD", text.casefold())
    out: list[str] = []
    prev = ""
    for ch in text:
        cat = unicodedata.category(ch)
        if cat == "Mn" and prev and ord(prev) < 0x0250:
            continue  # combining accent on a Latin letter: á → a
        if ch == "&":
            out.append(" and ")
        elif cat[0] in "PSZC":
            out.append(" ")
        else:
            out.append(ch)
        if cat != "Mn":
            prev = ch
    return _SPACES.sub(" ", unicodedata.normalize("NFC", "".join(out))).strip()


def _collapse(text: str) -> str:
    return _SPACES.sub(" ", text).strip(" -–—|")


def clean_artist(artist: str) -> tuple[str, tuple[str, ...]]:
    """Return (primary credit, featured artists) with channel suffixes removed."""
    artist = _TOPIC.sub("", artist.strip())
    if _VEVO.search(artist):
        artist = _VEVO.sub("", artist)
        if " " not in artist:
            artist = _CAMEL.sub(" ", artist)  # TaylorSwiftVEVO → Taylor Swift
    featured: list[str] = []
    m = _FEAT_PAREN.search(artist) or _FEAT_TAIL.search(artist)
    if m:
        featured.extend(p for p in _SPLIT_CREDIT.split(m.group("who").strip()) if p)
        artist = artist[: m.start()] + artist[m.end() :]
    return _collapse(artist), tuple(featured)


def clean_title(title: str, artist: str = "") -> tuple[str, tuple[str, ...]]:
    """Return (clean title, featured artists pulled out of the title)."""
    featured: list[str] = []
    t = title.strip()
    # YouTube credit tails: "Kesariya - Brahmastra | Ranbir Kapoor | Pritam | Arijit Singh"
    if " | " in t:
        t = t.split(" | ", 1)[0]
    for m in list(_FEAT_PAREN.finditer(t)):
        featured.extend(p for p in _SPLIT_CREDIT.split(m.group("who").strip()) if p)
    t = _FEAT_PAREN.sub("", t)
    tail = _FEAT_TAIL.search(t)
    if tail:
        featured.extend(p for p in _SPLIT_CREDIT.split(tail.group("who").strip()) if p)
        t = t[: tail.start()]
    for pat in _TITLE_NOISE:
        t = pat.sub("", t)
    # "Arijit Singh - Kesariya" uploaded by a channel: drop the artist prefix / suffix
    if artist:
        fa = fold(artist)
        parts = [p for p in re.split(r"\s+[-–—]\s+", t) if p]
        if len(parts) == 2:
            if fold(parts[0]) == fa:
                t = parts[1]
            elif fold(parts[1]) == fa:
                t = parts[0]
    return _collapse(t), tuple(featured)


def normalise(artist: str, title: str) -> NormalisedTrack:
    main_artist, feat_a = clean_artist(artist)
    clean_t, feat_t = clean_title(title, main_artist)
    featured = tuple(dict.fromkeys(f.strip() for f in (*feat_a, *feat_t) if f.strip()))
    clean_t = clean_t or title.strip()
    main_artist = main_artist or artist.strip()
    return NormalisedTrack(
        title=clean_t,
        artist=main_artist,
        featured=featured,
        norm_title=fold(clean_t),
        norm_artist=fold(main_artist),
    )
