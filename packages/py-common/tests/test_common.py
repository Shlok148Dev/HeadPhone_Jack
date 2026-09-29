import base64
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from cryptography.exceptions import InvalidTag

from jingle_common.crypto import TokenCipher
from jingle_common.enums import CardState, EventKind, Platform, Via, is_live_capable
from jingle_common.events import (
    ListenEvent,
    RawTrack,
    default_analytics_allowed,
    default_trainable,
    permitted_for_analytics,
    permitted_for_training,
)
from jingle_common.labels import freshness_label
from jingle_common.logging import redact

KEK = base64.b64decode("ZGV2LW9ubHktMzItYnl0ZS1rZXktZm9yLWxvY2FsISE=")


def test_crypto_roundtrip_and_tamper() -> None:
    c = TokenCipher(KEK, "k1")
    env = c.encrypt("secret-token", aad="user-1")
    assert "secret-token" not in env
    assert c.decrypt(env, aad="user-1") == "secret-token"
    with pytest.raises(InvalidTag):
        c.decrypt(env, aad="user-2")
    assert c.encrypt("x") != c.encrypt("x")


def test_crypto_rejects_other_key_id() -> None:
    env = TokenCipher(KEK, "k1").encrypt("t")
    with pytest.raises(ValueError):
        TokenCipher(KEK, "k2").decrypt(env)


def test_live_capability() -> None:
    assert is_live_capable(Via.COMPANION, Platform.APPLE_MUSIC)
    assert is_live_capable(Via.DIRECT, Platform.SPOTIFY)
    assert not is_live_capable(Via.DIRECT, Platform.APPLE_MUSIC)
    assert not is_live_capable(Via.EXPORT, Platform.YOUTUBE_MUSIC)


def _event(via: Via, platform: Platform) -> ListenEvent:
    now = datetime.now(UTC)
    return ListenEvent(
        user_id=uuid4(), raw=RawTrack(artist="a", title="t"), platform=platform, via=via,
        kind=EventKind.LISTEN, played_at=now, observed_at=now,
        trainable=default_trainable(via, platform),
    )


def test_training_lineage() -> None:
    assert not permitted_for_training(_event(Via.DIRECT, Platform.SPOTIFY))
    assert not permitted_for_training(_event(Via.LASTFM, Platform.SPOTIFY))
    assert permitted_for_training(_event(Via.COMPANION, Platform.SPOTIFY))
    assert permitted_for_training(_event(Via.LISTENBRAINZ, Platform.YOUTUBE_MUSIC))


def test_labels_never_contain_route_words() -> None:
    now = datetime(2026, 9, 29, 12, tzinfo=UTC)
    assert freshness_label(CardState.LIVE, Platform.SPOTIFY, now, now) == "Live on Spotify"
    assert (
        freshness_label(CardState.RECENT, Platform.APPLE_MUSIC, now - timedelta(seconds=120), now)
        == "2 min ago on Apple Music"
    )
    assert freshness_label(CardState.RECENT, Platform.UNKNOWN, now - timedelta(hours=3), now) == "3 h ago"
    assert freshness_label(CardState.RECENT, Platform.SPOTIFY, now, now, show_precise_time=False) == "Recently on Spotify"
    for word in ("ListenBrainz", "Last.fm", "via", "scrobb", "extension", "Companion"):
        assert word not in freshness_label(CardState.LIVE, Platform.YOUTUBE_MUSIC, now, now)


def test_redaction() -> None:
    assert "abc123" not in redact('Authorization: "Token abc123"'.replace("Token ", ""))
    assert "[EMAIL]" in redact("user a@b.com failed")


def test_analytics_lineage() -> None:
    assert not default_analytics_allowed(Via.DIRECT, Platform.SPOTIFY)
    assert not permitted_for_analytics(_event(Via.DIRECT, Platform.SPOTIFY))
    assert permitted_for_analytics(_event(Via.LASTFM, Platform.SPOTIFY))
    assert permitted_for_analytics(_event(Via.COMPANION, Platform.SPOTIFY))
