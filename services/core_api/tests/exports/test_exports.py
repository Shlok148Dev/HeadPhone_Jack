"""JNG-04-09 play a circle playlist in order in your own app: config, Apple token, YouTube matching,
export records. Tokens for the user's apps never reach the server (created in the browser)."""

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from circles import playlist
from circles import services as circles
from exports import services
from exports.models import TrackMatch
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def client(u):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(u)}")
    return c


@pytest.fixture
def circle():
    owner = UserFactory(username="owner")
    c = circles.create_circle(owner, "Crew")
    playlist.add(c, owner, title="Kasoor", artist="Prateek Kuhad")
    playlist.add(c, owner, title="Husn", artist="Anuv Jain")
    return c, owner


def test_config_reports_what_is_set_up(settings):
    settings.SPOTIFY_CLIENT_ID, settings.GOOGLE_OAUTH_CLIENT_ID, settings.YOUTUBE_API_KEY = (
        "sp-id",
        "",
        "",
    )
    settings.APPLE_MUSIC_TEAM_ID = ""
    c = client(UserFactory()).get("/api/v1/exports/config").json()
    assert c["spotify"] == {"enabled": True, "client_id": "sp-id"}
    assert c["youtube_music"]["enabled"] is False and c["apple_music"]["enabled"] is False
    assert c["amazon_music"]["enabled"] is False and "Amazon" in c["amazon_music"]["reason"]


def test_apple_developer_token_is_es256_with_kid(settings, tmp_path):
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    (tmp_path / "AuthKey.p8").write_bytes(pem)
    c = client(UserFactory())
    settings.APPLE_MUSIC_TEAM_ID = ""
    assert c.get("/api/v1/exports/apple/token").status_code == 404
    settings.APPLE_MUSIC_TEAM_ID, settings.APPLE_MUSIC_KEY_ID = "TEAM123", "KEY456"
    settings.APPLE_MUSIC_PRIVATE_KEY_PATH = str(tmp_path / "AuthKey.p8")
    tok = c.get("/api/v1/exports/apple/token").json()["token"]
    assert jwt.get_unverified_header(tok) == {"alg": "ES256", "kid": "KEY456", "typ": "JWT"}
    claims = jwt.decode(tok, key.public_key(), algorithms=["ES256"])
    assert claims["iss"] == "TEAM123" and claims["exp"] > claims["iat"]


def _yt(monkeypatch, handler):
    real = httpx.Client
    monkeypatch.setattr(
        services.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)
    )


def test_youtube_matching_prefers_official_audio_and_caches(settings, monkeypatch, circle):
    c, owner = circle
    settings.GOOGLE_OAUTH_CLIENT_ID, settings.YOUTUBE_API_KEY = "g-id", "yt-key"
    calls = []

    def handler(req):
        calls.append(req.url.params["q"])
        q = req.url.params["q"]
        if "Kasoor" in q:
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": {"videoId": "AAAAAAAAAAA"},
                            "snippet": {
                                "title": "Kasoor (lyrics) fan edit",
                                "channelTitle": "Random Uploads",
                            },
                        },
                        {
                            "id": {"videoId": "BBBBBBBBBBB"},
                            "snippet": {"title": "Kasoor", "channelTitle": "Prateek Kuhad - Topic"},
                        },
                    ]
                },
            )
        return httpx.Response(200, json={"items": []})

    _yt(monkeypatch, handler)
    url = f"/api/v1/circles/{c.pk}/playlist/youtube-matches"
    m = client(owner).post(url).json()["matches"]
    assert list(m.values()) == ["BBBBBBBBBBB", None]  # official audio wins; not found stays None
    assert (
        client(owner).post(url).json()["matches"] == m and len(calls) == 2
    )  # cached, no new searches
    assert TrackMatch.objects.get(external_id="BBBBBBBBBBB").platform == "youtube_music"
    assert client(UserFactory()).post(url).status_code == 404  # members only


def test_youtube_quota_exhausted_caches_nothing(settings, monkeypatch, circle):
    c, owner = circle
    settings.GOOGLE_OAUTH_CLIENT_ID, settings.YOUTUBE_API_KEY = "g-id", "yt-key"
    _yt(
        monkeypatch,
        lambda req: httpx.Response(403, json={"error": {"errors": [{"reason": "quotaExceeded"}]}}),
    )
    m = client(owner).post(f"/api/v1/circles/{c.pk}/playlist/youtube-matches").json()["matches"]
    assert set(m.values()) == {None} and not TrackMatch.objects.exists()  # retried tomorrow


def test_export_records_validate_and_round_trip(circle):
    c, owner = circle
    api = client(owner)
    base = f"/api/v1/circles/{c.pk}/playlist/exports"
    ok = {
        "external_id": "37i9dQZF1DX",
        "url": "https://open.spotify.com/playlist/37i9dQZF1DX",
        "track_keys": ["a|b"],
    }
    assert api.put(f"{base}/spotify", ok, format="json").status_code == 200
    assert api.get(base).json()["spotify"]["url"] == ok["url"]
    bad = {**ok, "url": "https://evil.example/phish"}
    assert (
        api.put(f"{base}/spotify", bad, format="json").status_code == 400
    )  # only the app's own domain
    assert api.put(f"{base}/myspace", ok, format="json").status_code == 404
    assert client(UserFactory()).get(base).status_code == 404
