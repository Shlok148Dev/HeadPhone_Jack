"""YouTube Music history from a Google Takeout export (JNG-01-06, ADR-0015).

Accepts ``watch-history.json`` (streamed with ijson) and the default ``watch-history.html``.
Only YouTube Music entries are kept (``header == "YouTube Music"`` or a music.youtube.com link).
Titles are cleaned; "Artist - Topic" channels become the artist. Plays land as ``via=EXPORT``,
which can never be Live (BR-01).
"""

import html
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import IO, Any

import ijson
from jingle_common.enums import Platform
from jingle_common.events import RawTrack

from .push.platform import safe_platform_url
from .record import Play

MAX_BYTES = 50 * 1024 * 1024  # NFR-PERF-07 / SEC-07
_WATCHED = re.compile(r"^(Watched|Listened to|Played)\s+", re.I)
_TOPIC = re.compile(r"\s*-\s*Topic$", re.I)


class TakeoutError(Exception):
    """The file is not a usable Takeout export. Message is safe to show the user."""


@dataclass
class TakeoutEntry:
    title: str
    artist: str
    url: str | None
    time: datetime


def _clean_title(raw: str) -> str:
    return _WATCHED.sub("", html.unescape(raw)).strip()


def _clean_artist(raw: str) -> str:
    return _TOPIC.sub("", html.unescape(raw)).strip()


def _parse_time(raw: str) -> datetime | None:
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_music(header: str | None, url: str | None) -> bool:
    return (header or "").strip() == "YouTube Music" or "music.youtube.com" in (url or "")


def parse_json(fp: IO[bytes]) -> Iterator[TakeoutEntry]:
    try:
        for item in ijson.items(fp, "item"):
            yield from _entry_from_json(item)
    except ijson.JSONError:
        raise TakeoutError(
            "That file isn't a valid watch-history.json from Google Takeout."
        ) from None


def _entry_from_json(item: Any) -> Iterator[TakeoutEntry]:
    if not isinstance(item, dict):
        return
    url = item.get("titleUrl")
    if not _is_music(item.get("header"), url):
        return
    subtitles = item.get("subtitles") or []
    artist = subtitles[0].get("name", "") if subtitles and isinstance(subtitles[0], dict) else ""
    when = _parse_time(str(item.get("time", "")))
    title = _clean_title(str(item.get("title", "")))
    if title and artist and when:
        yield TakeoutEntry(title=title, artist=_clean_artist(artist), url=url, time=when)


class _HistoryHTML(HTMLParser):
    """Parses Takeout's HTML: each entry is an outer-cell div with header, links and a date."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[TakeoutEntry] = []
        self._depth = 0
        self._cell_depth: int | None = None
        self._header: str | None = None
        self._links: list[tuple[str, str]] = []
        self._text: list[str] = []
        self._href: str | None = None
        self._in_header = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        cls = dict(attrs).get("class") or ""
        if tag == "div":
            self._depth += 1
            if "outer-cell" in cls:
                self._cell_depth, self._header, self._links, self._text = self._depth, None, [], []
            if "header-cell" in cls and self._cell_depth is not None:
                self._in_header = True
        elif tag == "a" and self._cell_depth is not None:
            self._href = dict(attrs).get("href") or ""
            self._links.append((self._href, ""))

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self._href = None
        if tag != "div":
            return
        if self._in_header:
            self._in_header = False
        if self._cell_depth is not None and self._depth == self._cell_depth:
            self._finish_cell()
            self._cell_depth = None
        self._depth -= 1

    def handle_data(self, data: str) -> None:
        if self._cell_depth is None:
            return
        text = data.strip()
        if not text:
            return
        if self._in_header:
            self._header = (self._header or "") + text
        elif self._href is not None and self._links:
            href, prev = self._links[-1]
            self._links[-1] = (href, (prev + " " + text).strip())
        else:
            self._text.append(text)

    def _finish_cell(self) -> None:
        if not self._links:
            return
        url, title = self._links[0]
        if not _is_music(self._header, url):
            return
        artist = self._links[1][1] if len(self._links) > 1 else ""
        when = None
        for chunk in reversed(self._text):
            when = _parse_takeout_html_time(chunk)
            if when:
                break
        title = _clean_title(title)
        if title and artist and when:
            self.entries.append(
                TakeoutEntry(title=title, artist=_clean_artist(artist), url=url, time=when)
            )


_HTML_TIME = re.compile(r"(\w{3} \d{1,2}, \d{4}, \d{1,2}:\d{2}:\d{2}\s?[AP]M)\s*(\w+)?")


def _parse_takeout_html_time(text: str) -> datetime | None:
    """Takeout HTML dates look like ``Sep 28, 2026, 9:14:03 PM IST``. Timezone names are
    ambiguous, so IST is honoured and anything else is treated as UTC."""
    from datetime import UTC, timedelta, timezone

    m = _HTML_TIME.search(text.replace(" ", " "))
    if not m:
        return None
    try:
        naive = datetime.strptime(m.group(1).replace("  ", " "), "%b %d, %Y, %I:%M:%S %p")
    except ValueError:
        return None
    tz = timezone(timedelta(hours=5, minutes=30)) if (m.group(2) or "").upper() == "IST" else UTC
    return naive.replace(tzinfo=tz)


def parse_html(data: bytes) -> Iterator[TakeoutEntry]:
    parser = _HistoryHTML()
    try:
        parser.feed(data.decode("utf-8", errors="replace"))
        parser.close()
    except Exception:  # noqa: BLE001 - malformed HTML
        raise TakeoutError(
            "That file isn't a valid watch-history.html from Google Takeout."
        ) from None
    yield from parser.entries


def to_plays(entries: Iterator[TakeoutEntry]) -> list[Play]:
    plays: list[Play] = []
    for e in entries:
        links = {}
        if url := safe_platform_url(e.url, Platform.YOUTUBE_MUSIC):
            links[Platform.YOUTUBE_MUSIC] = url
        plays.append(
            Play(
                track=RawTrack(artist=e.artist[:500], title=e.title[:500]),
                played_at=e.time,
                platform=Platform.YOUTUBE_MUSIC,
                links=links,
            )
        )
    return plays


def sniff_and_parse(path: str) -> list[Play]:
    """Parse a stored upload by content (not by the user-supplied filename)."""
    with open(path, "rb") as fp:
        head = fp.read(512).lstrip()
        fp.seek(0)
        if head.startswith(b"[") or head.startswith(b"\xef\xbb\xbf["):
            if head.startswith(b"\xef\xbb\xbf"):
                fp.read(3)
            return to_plays(parse_json(fp))
        if b"<html" in head.lower() or b"<!doctype" in head.lower() or b"<div" in head.lower():
            return to_plays(parse_html(fp.read()))
    raise TakeoutError("Upload watch-history.json or watch-history.html from Google Takeout.")
