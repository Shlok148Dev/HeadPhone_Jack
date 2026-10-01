"""Artwork service: real covers only, colours that keep text readable (docs/ux/DECISIONS.md)."""

import io

import httpx
import pytest
from PIL import Image
from rest_framework.test import APIClient

from artwork import services
from artwork.models import Artwork

pytestmark = pytest.mark.django_db


def png(color) -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (100, 100), color).save(b, "PNG")
    return b.getvalue()


def test_keys_ignore_features_and_punctuation():
    assert (
        services.track_key('Kesariya (From "Brahmastra")', "Arijit Singh")
        == "arijit singh|kesariya"
    )
    assert services.track_key("Blinding Lights", "The Weeknd") == services.track_key(
        "blinding lights!", "the weeknd"
    )


def test_colours_pass_contrast_for_text_in_both_themes():
    for c in [(250, 230, 40), (20, 20, 20), (200, 30, 120), (90, 200, 250)]:
        cols = services.extract_colors(png(c))
        dark = tuple(int(cols["ambient_dark"][i : i + 2], 16) for i in (1, 3, 5))
        light = tuple(int(cols["ambient_light"][i : i + 2], 16) for i in (1, 3, 5))
        assert services.contrast(dark, (244, 244, 247)) >= 4.5
        assert services.contrast(light, (17, 17, 24)) >= 4.5


def test_misses_are_queued_not_fetched(fake_redis):
    items = services.enrich([{"title": "Kasoor", "artist": "Prateek Kuhad"}])
    assert items[0]["artwork_url"] is None and items[0]["artwork_colors"] is None
    assert fake_redis.smembers(services.QUEUE) == {"track\tKasoor\tPrateek Kuhad"}


def _transport(results: dict):
    def handler(request: httpx.Request):
        if request.url.host == "itunes.apple.com":
            return httpx.Response(
                200, json={"results": results.get(request.url.params["entity"], [])}
            )
        return httpx.Response(200, content=png((180, 60, 40)))

    return httpx.MockTransport(handler)


def test_resolve_picks_the_right_song_and_sizes_urls():
    song = {
        "trackName": "Kasoor",
        "artistName": "Prateek Kuhad",
        "trackId": 1,
        "artworkUrl100": "https://is1-ssl.mzstatic.com/image/thumb/x/cover.jpg/100x100bb.jpg",
    }
    other = {**song, "trackName": "Something Else", "trackId": 2}
    with httpx.Client(transport=_transport({"song": [other, song]})) as c:
        a = services.resolve("track", "Kasoor", "Prateek Kuhad", c)
    assert a.status == "found" and a.source_id == "1"
    assert a.url.endswith("/600x600bb.jpg") and a.url_small.endswith("/120x120bb.jpg")
    assert a.colors["dominant"].startswith("#")
    got = services.enrich([{"title": "Kasoor", "artist": "Prateek Kuhad"}])[0]
    assert got["artwork_url"] == a.url and got["artwork_colors"]["ambient_dark"]


def test_no_good_match_is_recorded_as_missing_never_faked():
    wrong = {
        "trackName": "Totally Different",
        "artistName": "Nobody",
        "artworkUrl100": "https://x/100x100bb.jpg",
    }
    with httpx.Client(transport=_transport({"song": [wrong]})) as c:
        a = services.resolve("track", "Kasoor", "Prateek Kuhad", c)
    assert a.status == "missing" and a.url == ""
    assert (
        services.enrich([{"title": "Kasoor", "artist": "Prateek Kuhad"}])[0]["artwork_url"] is None
    )


def test_artist_uses_their_own_album_cover():
    album = {
        "collectionName": "cold/mess",
        "artistName": "Prateek Kuhad",
        "collectionId": 9,
        "artworkUrl100": "https://x/a/100x100bb.jpg",
    }
    with httpx.Client(transport=_transport({"album": [album]})) as c:
        a = services.resolve("artist", "", "Prateek Kuhad", c)
    assert a.status == "found" and a.kind == "artist"
    assert services.enrich_artists([{"name": "Prateek Kuhad"}])[0]["image_url"].endswith(
        "120x120bb.jpg"
    )


def test_drain_respects_its_limit(fake_redis, monkeypatch):
    calls = []
    monkeypatch.setattr(services, "resolve", lambda kind, t, a, c: calls.append((kind, t, a)))
    for i in range(20):
        fake_redis.sadd(services.QUEUE, f"track\tSong {i}\tArtist")
    assert services.drain(limit=15) == 15 and len(calls) == 15
    assert fake_redis.scard(services.QUEUE) == 5


def test_wall_is_public_and_only_real_covers():
    Artwork.objects.create(
        kind="track",
        key="a|b",
        status="found",
        source="itunes",
        url="https://x/600x600bb.jpg",
        url_small="https://x/120.jpg",
        colors={"dominant": "#112233"},
    )
    Artwork.objects.create(kind="track", key="c|d", status="missing", source="itunes")
    covers = APIClient().get("/api/v1/artwork/wall").json()["covers"]
    assert [c["url"] for c in covers] == ["https://x/600x600bb.jpg"]


def test_prefers_the_original_over_lofi_and_remixes():
    lofi = {"trackName": "Kesariya (Lofi Flip)", "artistName": "Arijit Singh"}
    remix = {"trackName": "Kesariya Remix", "artistName": "Arijit Singh"}
    original = {"trackName": 'Kesariya (From "Brahmastra")', "artistName": "Pritam, Arijit Singh"}
    scores = {
        k: services._score(r, "Kesariya", "Arijit Singh")
        for k, r in {"lofi": lofi, "remix": remix, "original": original}.items()
    }
    assert max(scores, key=scores.get) == "original"
    # …unless a variant is what was asked for.
    assert services._score(remix, "Kesariya Remix", "Arijit Singh") > services._score(
        original, "Kesariya Remix", "Arijit Singh"
    )
