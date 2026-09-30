"""CONTRACTS.md §7 card resolution (JNG-05-01; BR-01, BR-02, BR-03, BR-14)."""

from datetime import UTC, datetime, timedelta
from unittest import mock

import pytest
import redis

from feed import resolver
from feed.resolver import resolve_card
from sources.models import Recording, RecordingLink
from tests.factories import UserFactory, put_signal

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 9, 29, 10, 15, 30, tzinfo=UTC)
T = NOW.timestamp()


def _has_key(obj, key):
    if isinstance(obj, dict):
        return key in obj or any(_has_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_key(v, key) for v in obj)
    return False


@pytest.fixture
def owner(db):
    return UserFactory(username="kabir", display_name="Kabir")


@pytest.fixture
def stranger(db):
    return UserFactory(username="stranger")


class TestLive:
    @pytest.mark.parametrize(
        "via,platform",
        [("COMPANION", "YOUTUBE_MUSIC"), ("LISTENBRAINZ", "APPLE_MUSIC"), ("LASTFM", "SPOTIFY"),
         ("DIRECT", "SPOTIFY"), ("COMPANION", "AMAZON_MUSIC")],
    )
    def test_fresh_live_capable_signal_is_live(self, owner, fake_redis, via, platform):
        put_signal(fake_redis, "np", owner.pk, observed_at=T - 10, via=via, platform=platform)
        card = resolve_card(owner, owner, NOW)
        assert card["state"] == "LIVE"
        assert card["platform"] == platform
        assert card["freshness_label"].startswith("Live")
        assert card["observed_at"] == "2026-09-29T10:15:20Z"
        assert not _has_key(card, "via")

    @pytest.mark.parametrize(
        "via,platform", [("DIRECT", "APPLE_MUSIC"), ("DIRECT", "AMAZON_MUSIC"),
                         ("EXPORT", "YOUTUBE_MUSIC"), ("BOGUS", "SPOTIFY")],
    )
    def test_non_live_capable_never_live(self, owner, fake_redis, via, platform):
        put_signal(fake_redis, "np", owner.pk, observed_at=T - 5, via=via, platform=platform)
        card = resolve_card(owner, owner, NOW)
        assert card["state"] == "RECENT"

    def test_89s_live_90s_not(self, owner, fake_redis):
        put_signal(fake_redis, "np", owner.pk, observed_at=T - 89)
        assert resolve_card(owner, owner, NOW)["state"] == "LIVE"
        put_signal(fake_redis, "np", owner.pk, observed_at=T - 90)
        card = resolve_card(owner, owner, NOW)
        assert card["state"] == "RECENT"
        assert card["freshness_label"] == "1 min ago on Spotify"

    def test_far_future_signal_not_live(self, owner, fake_redis):
        put_signal(fake_redis, "np", owner.pk, observed_at=T + 3600)
        assert resolve_card(owner, owner, NOW)["state"] == "RECENT"

    def test_missing_observed_at_not_live(self, owner, fake_redis):
        fake_redis.hset(f"np:{owner.pk}", mapping={"event": "{bad json", "via": "COMPANION",
                                                    "platform": "SPOTIFY"})
        card = resolve_card(owner, owner, NOW)
        assert card["state"] == "HIDDEN"


class TestRecentTop:
    def test_recent_from_last(self, owner, fake_redis):
        put_signal(fake_redis, "last", owner.pk, observed_at=T - 3 * 3600,
                   platform="APPLE_MUSIC", via="LISTENBRAINZ", title="Espresso")
        card = resolve_card(owner, owner, NOW)
        assert card["state"] == "RECENT"
        assert card["freshness_label"] == "3 h ago on Apple Music"
        assert card["recording"]["title"] == "Espresso"
        assert card["attribution"] is None

    def test_newest_recent_wins(self, owner, fake_redis):
        put_signal(fake_redis, "np", owner.pk, observed_at=T - 600, title="Newer",
                   via="DIRECT", platform="APPLE_MUSIC")
        put_signal(fake_redis, "last", owner.pk, observed_at=T - 7200, title="Older")
        assert resolve_card(owner, owner, NOW)["recording"]["title"] == "Newer"

    def test_attribution_only_for_direct_spotify(self, owner, fake_redis):
        put_signal(fake_redis, "last", owner.pk, observed_at=T - 60, via="DIRECT",
                   platform="SPOTIFY")
        assert resolve_card(owner, owner, NOW)["attribution"] == "SPOTIFY"
        put_signal(fake_redis, "last", owner.pk, observed_at=T - 60, via="COMPANION",
                   platform="SPOTIFY")
        assert resolve_card(owner, owner, NOW)["attribution"] is None

    def test_top_from_mongo(self, owner, mongo_db):
        uid = str(owner.pk)
        docs = []
        for i in range(3):
            docs.append({"user_id": uid, "played_at": NOW - timedelta(days=1, minutes=i),
                         "raw": {"artist": "SZA", "title": "Snooze"}, "platform": "SPOTIFY",
                         "via": "COMPANION"})
        docs.append({"meta": {"user_id": uid, "platform": "APPLE_MUSIC", "via": "EXPORT"},
                     "played_at": NOW - timedelta(days=2),
                     "raw": {"artist": "Arijit", "title": "Kesariya"}})
        docs.append({"user_id": uid, "played_at": NOW - timedelta(days=45),
                     "raw": {"artist": "Old", "title": "Old"}} )
        docs[-1].update({"platform": "SPOTIFY"})
        for _ in range(5):
            mongo_db.listens.insert_one(dict(docs[-1]))
        mongo_db.listens.insert_many(docs[:-1])
        card = resolve_card(owner, owner, NOW)
        assert card["state"] == "TOP"
        assert card["freshness_label"] == "Top this month"
        assert card["recording"]["title"] == "Snooze"
        assert "observed_at" not in card

    def test_nothing_is_hidden(self, owner):
        card = resolve_card(owner, owner, NOW)
        assert card["state"] == "HIDDEN"
        assert card["recording"] is None and card["platform"] is None
        assert card["freshness_label"] == "No plays yet"  # nothing captured is not "Hidden"
        assert card["degraded"] is False

    def test_mongo_unavailable_marks_degraded(self, owner, monkeypatch):
        monkeypatch.setattr(resolver, "get_db", lambda: None)
        card = resolve_card(owner, owner, NOW)
        assert card["state"] == "HIDDEN" and card["degraded"] is True

    def test_mongo_error_marks_degraded(self, owner, monkeypatch):
        broken = mock.Mock()
        broken.listens.aggregate.side_effect = RuntimeError("down")
        monkeypatch.setattr(resolver, "get_db", lambda: broken)
        assert resolve_card(owner, owner, NOW)["degraded"] is True

    def test_redis_down_falls_back_to_latest_listen(self, owner, mongo_db, monkeypatch):
        broken = mock.Mock()
        broken.pipeline.side_effect = redis.ConnectionError("down")
        monkeypatch.setattr(resolver, "get_redis", lambda: broken)
        mongo_db.listens.insert_one({"user_id": str(owner.pk), "platform": "SPOTIFY",
                                     "via": "COMPANION", "raw": {"artist": "A", "title": "B"},
                                     "played_at": datetime(2026, 9, 29, 10, 0)})
        card = resolve_card(owner, owner, NOW)
        assert card["state"] == "RECENT"
        assert card["degraded"] is True
        assert card["freshness_label"] == "15 min ago on Spotify"

    def test_redis_down_and_mongo_down(self, owner, monkeypatch):
        broken = mock.Mock()
        broken.pipeline.side_effect = redis.ConnectionError("down")
        monkeypatch.setattr(resolver, "get_redis", lambda: broken)
        monkeypatch.setattr(resolver, "get_db", lambda: None)
        assert resolve_card(owner, owner, NOW)["degraded"] is True

    def test_latest_listen_query_error(self, owner, monkeypatch):
        broken_db = mock.Mock()
        broken_db.listens.find_one.side_effect = RuntimeError
        monkeypatch.setattr(resolver, "get_db", lambda: broken_db)
        assert resolver._latest_listen(str(owner.pk)) is None

    def test_naive_now_is_treated_as_utc(self, owner, fake_redis):
        put_signal(fake_redis, "np", owner.pk, observed_at=T - 10)
        assert resolve_card(owner, owner, NOW.replace(tzinfo=None))["state"] == "LIVE"


class TestRecordingLinks:
    def test_links_from_recording(self, owner, fake_redis):
        rec = Recording.objects.create(title="Kill Bill", artist_name="SZA", norm_key="sza|kill bill")
        RecordingLink.objects.create(recording=rec, platform="SPOTIFY",
                                     url="https://open.spotify.com/track/x")
        put_signal(fake_redis, "last", owner.pk, observed_at=T - 60, recording_id=rec.pk)
        card = resolve_card(owner, owner, NOW)
        assert card["recording"]["id"] == str(rec.pk)
        assert card["recording"]["links"] == {
            "SPOTIFY": "https://open.spotify.com/track/x", "APPLE_MUSIC": None,
            "AMAZON_MUSIC": None, "YOUTUBE_MUSIC": None,
        }

    def test_bad_recording_id(self):
        assert resolver._links("not-a-uuid")["SPOTIFY"] is None


class TestPrivacy:
    def test_stranger_sees_hidden(self, owner, stranger, fake_redis):
        put_signal(fake_redis, "np", owner.pk, observed_at=T - 5)
        card = resolve_card(owner, stranger, NOW)
        assert card["state"] == "HIDDEN" and card["recording"] is None

    def test_friend_sees_card_and_hide_last_active(self, owner, stranger, fake_redis, monkeypatch):
        monkeypatch.setattr("core_api.policy.are_friends", lambda a, b: True)
        put_signal(fake_redis, "last", owner.pk, observed_at=T - 300, platform="YOUTUBE_MUSIC")
        card = resolve_card(owner, stranger, NOW)
        assert card["state"] == "RECENT"
        assert card["freshness_label"] == "5 min ago on YouTube Music"
        owner.privacy.show_last_active = False
        owner.privacy.save()
        owner._privacy_cache = None
        card = resolve_card(owner, stranger, NOW)
        assert "observed_at" not in card
        assert card["freshness_label"] == "Recently on YouTube Music"
        # the owner still sees precise time on their own card
        assert resolve_card(owner, owner, NOW)["observed_at"]

    def test_private_mode_hides_from_friends_not_owner(self, owner, stranger, fake_redis,
                                                        monkeypatch):
        monkeypatch.setattr("core_api.policy.are_friends", lambda a, b: True)
        put_signal(fake_redis, "np", owner.pk, observed_at=T - 5)
        owner.private_until = NOW + timedelta(hours=1)
        assert resolve_card(owner, stranger, NOW)["state"] == "HIDDEN"
        assert resolve_card(owner, owner, NOW)["state"] == "LIVE"

    def test_visibility_nobody(self, owner, stranger, fake_redis, monkeypatch):
        monkeypatch.setattr("core_api.policy.are_friends", lambda a, b: True)
        put_signal(fake_redis, "np", owner.pk, observed_at=T - 5)
        owner.privacy.activity_visibility = "nobody"
        owner.privacy.save()
        assert resolve_card(owner, stranger, NOW)["state"] == "HIDDEN"
