"""Seed the demo world (ADR-0010). Idempotent; refuses to run unless JINGLE_DEMO=1.

Seeding writes ``scrobble_tokens`` rows directly, a documented exception to ADR-0006 (ingest-ml
normally mints them): the tokens are deterministic (``jingle_common.demo.demo_token``) so the
simulator can derive them without a shared file.
"""

import hashlib
import logging
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from jingle_common.demo import DEMO_EMAIL, DEMO_PASSWORD_DEFAULT, PERSONAS, demo_token

from accounts.models import ConsentPurpose, User
from accounts.services import active_consent, create_account, give_consent
from social.models import Friendship, FriendshipStatus
from sources.models import ScrobbleToken

log = logging.getLogger(__name__)

# Demo friendships (Sprint 3): the demo login knows most personas; one request waits for it.
FRIENDS_OF_DEMO = (
    "aanya",
    "kabir",
    "meera",
    "dev",
    "riya",
    "arjun",
    "zoya",
    "ishaan",
    "tara",
    "vikram",
    "sana",
)
PENDING_TO_DEMO = ("neel",)
PERSONA_PAIRS = (
    ("aanya", "kabir"),
    ("aanya", "dev"),
    ("meera", "zoya"),
    ("dev", "ishaan"),
    ("riya", "tara"),
    ("neel", "kabir"),
    ("kiara", "aanya"),
    ("kiara", "kabir"),
    ("rohan", "dev"),
    ("rohan", "ishaan"),
)


class Command(BaseCommand):
    help = "Seed the demo world: a demo login and about 12 friends across four platforms."

    def handle(self, *args, **options):
        if not settings.JINGLE_DEMO:
            raise CommandError("seed_demo only runs with JINGLE_DEMO=1")
        password = os.environ.get("DEMO_PASSWORD") or DEMO_PASSWORD_DEFAULT
        created = 0
        with transaction.atomic():
            for p in PERSONAS:
                email = DEMO_EMAIL if p.username == "demo" else f"{p.username}@demo.jingle.local"
                user = User.objects.filter(username=p.username).first()
                if user is None:
                    user = create_account(
                        email=email,
                        username=p.username,
                        # Only the demo login can sign in; friends are data-only accounts.
                        password=password if p.username == "demo" else None,
                        display_name=p.display_name,
                        birth_year=2001,
                    )
                    user.college, user.city, user.discoverable = p.college, p.city, True
                    user.save(update_fields=["college", "city", "discoverable"])
                    created += 1
                for purpose in (
                    ConsentPurpose.ACTIVITY_SHARING,
                    ConsentPurpose.SUGGESTIONS_DISCOVERABILITY,
                ):
                    if active_consent(user, purpose) is None:
                        give_consent(user, purpose)
                token = demo_token(p.username, settings.SERVICE_TOKEN)
                ScrobbleToken.objects.get_or_create(
                    token_sha256=hashlib.sha256(token.encode()).hexdigest(),
                    defaults={"user": user, "label": "Demo simulator"},
                )
            users = {
                u.username: u
                for u in User.objects.filter(username__in=[p.username for p in PERSONAS])
            }
            pairs = [("demo", n, True) for n in FRIENDS_OF_DEMO] + [
                (a, b, True) for a, b in PERSONA_PAIRS
            ]
            pairs += [(n, "demo", False) for n in PENDING_TO_DEMO]
            for a, b, accepted in pairs:
                low, high = Friendship.ordered(users[a].pk, users[b].pk)
                Friendship.objects.get_or_create(
                    user_low_id=low,
                    user_high_id=high,
                    defaults={
                        "requested_by": users[a],
                        "status": FriendshipStatus.ACCEPTED
                        if accepted
                        else FriendshipStatus.PENDING,
                        "accepted_at": timezone.now() if accepted else None,
                    },
                )
        self._reset_demo_sandbox(users["demo"])
        self._seed_circles()
        self._seed_sends(users)
        self._seed_blend(users)
        self._seed_genres()
        self._seed_rituals(users)
        self._seed_trust(users, password)
        # Real covers for every catalogue track and artist; the worker resolves the queue at the
        # iTunes Search API's pace (docs/ux/DECISIONS.md D-ART-02).
        from artwork.management.commands.resolve_artwork import queue_demo_catalogue

        queue_demo_catalogue()
        # Personas' Daily Drops for today so far (JNG-14-01); the beat task adds the rest.
        from drops.tasks import demo_drops

        demo_drops()
        # Shared circle playlists (JNG-04-08): a few songs each, added by members, if empty.
        _seed_circle_playlists()
        # Weekly charts from the demo listening history (backfills first plays on the first run).
        from charts.services import refresh_active

        refresh_active()
        # Suggestions once the simulator has backfilled listening history (ADR-0010, Sprint 5).
        from jingle_ml.tasks import schedule_all_later

        schedule_all_later(120)
        self.stdout.write(f"demo world ready ({created} new users; login {DEMO_EMAIL})")

    def _reset_demo_sandbox(self, demo):
        """Demo is a sandbox login: each start clears its own pending requests to personas and its
        suggestion dismissals, so the demo world (and the suggestions E2E) is repeatable."""
        from django.db.models import Q

        from suggestions.models import SuggestionFeedback

        Friendship.objects.filter(
            Q(user_low=demo) | Q(user_high=demo),
            requested_by=demo,
            status=FriendshipStatus.PENDING,
        ).delete()
        SuggestionFeedback.objects.filter(user=demo).delete()
        # Leftovers from interrupted E2E runs must not show up in the demo world.
        from blends.models import Blend
        from circles.models import Circle

        Circle.objects.filter(name__startswith="E2E crew").delete()
        Blend.objects.filter(members__user=demo).exclude(name="Demo + Aanya + Kabir").delete()

    def _seed_sends(self, users):
        """A song and a mixtape in demo's inbox, and one send out, so EP-06 isn't empty."""
        from jingle_common.demo import CATALOG

        from sends import services as sends
        from sends.models import Recommendation

        if Recommendation.objects.filter(sender__username__in=["aanya", "kabir"]).exists():
            return

        def song(t):
            return {"title": t.title, "artist": t.artist}

        demo = users["demo"]
        sends.send(
            users["aanya"],
            [song(CATALOG[4])],
            note="This one's been on repeat since the fest. Trust me.",
            user_ids=[demo.pk],
        )
        sends.send(
            users["kabir"],
            [song(t) for t in CATALOG[:6]],
            note="Road trip mixtape for Saturday",
            user_ids=[demo.pk],
        )
        sends.send(demo, [song(CATALOG[5])], note="You'll like this", user_ids=[users["zoya"].pk])

    def _seed_blend(self, users):
        """Demo + Aanya + Kabir. Mixed once the simulator has backfilled some plays."""
        from blends import services as blends
        from blends.models import Blend
        from blends.tasks import regenerate

        b = Blend.objects.filter(name="Demo + Aanya + Kabir", created_by=users["demo"]).first()
        if b is None:
            b = blends.create(
                users["demo"],
                user_ids=[users["aanya"].pk, users["kabir"].pk],
                name="Demo + Aanya + Kabir",
            )
        try:
            regenerate.apply_async(args=[str(b.pk)], countdown=150)
        except Exception:  # noqa: BLE001 - broker down: the Blend can be regenerated by hand
            self.stdout.write("blend refresh not scheduled (broker unavailable)")

    # Demo-only stand-in for MusicBrainz tags, which need network resolution (ADR-0022).
    DEMO_TAGS = {
        "A.R. Rahman": ["filmi", "indian classical"],
        "AP Dhillon": ["punjabi", "hip hop"],
        "Anuv Jain": ["indie pop", "acoustic"],
        "Arijit Singh": ["bollywood", "filmi"],
        "Billie Eilish": ["pop", "alternative"],
        "Diljit Dosanjh": ["punjabi", "pop"],
        "Dua Lipa": ["pop", "dance"],
        "Frank Ocean": ["r&b", "alternative"],
        "Kendrick Lamar": ["hip hop", "rap"],
        "Lucky Ali": ["indie pop", "indian pop"],
        "Prateek Kuhad": ["indie pop", "acoustic"],
        "Pritam": ["bollywood", "filmi"],
        "Radiohead": ["alternative", "rock"],
        "SZA": ["r&b", "pop"],
        "Tame Impala": ["psychedelic", "alternative"],
        "Taylor Swift": ["pop", "country"],
        "The Local Train": ["indian rock", "indie"],
        "The Weeknd": ["r&b", "pop"],
    }

    def _seed_genres(self):
        from sources.models import Artist, ArtistTag

        for name, tags in self.DEMO_TAGS.items():
            artist = Artist.objects.filter(name=name).first() or Artist.objects.create(name=name)
            for i, tag in enumerate(tags):
                ArtistTag.objects.get_or_create(
                    artist=artist, tag=tag, defaults={"weight": 1.0 - 0.3 * i}
                )

    def _seed_rituals(self, users):
        """Last week's battle with results, this week's nominations, and demo's recap."""
        from datetime import timedelta

        from jingle_common.demo import CATALOG

        from circles.models import Circle
        from rituals import services as rituals
        from rituals.models import Battle, BattleVote, Nomination, Recap

        circle = Circle.objects.filter(name="KJ Somaiya crew").first()
        if circle is None:
            return
        crew = [users[n] for n in ("demo", "aanya", "kabir", "dev", "ishaan")]
        now = timezone.now()
        week = rituals.week_of(now)
        last = week - timedelta(days=7)
        nominate, vote, close = rituals._times(circle, last)
        b, created = Battle.objects.get_or_create(
            circle=circle,
            week=last,
            defaults={"nominate_opens": nominate, "vote_opens": vote, "closes_at": close},
        )
        if created:
            noms = [
                Nomination.objects.create(
                    battle=b, user=u, title=CATALOG[i].title, artist=CATALOG[i].artist
                )
                for i, u in enumerate(crew[1:])
            ]
            for voter, pick in (
                (crew[0], 0),
                (crew[2], 0),
                (crew[3], 1),
                (crew[4], 0),
                (crew[1], 2),
            ):
                if noms[pick].user_id != voter.pk:
                    BattleVote.objects.get_or_create(battle=b, nomination=noms[pick], voter=voter)
            b.results = rituals.leaderboard(b)
            b.closed_at = close
            b.save(update_fields=["results", "closed_at"])
        current = rituals.battle_for(circle, now)
        if current.week == week and rituals.phase(current, now) in ("nominating", "voting"):
            for i, u in enumerate(crew[1:4]):
                Nomination.objects.get_or_create(
                    battle=current,
                    user=u,
                    defaults={"title": CATALOG[6 + i].title, "artist": CATALOG[6 + i].artist},
                )
        month = rituals.previous_month(now)
        if not Recap.objects.filter(user=users["demo"], month=month).exists():
            data = rituals.build_recap(users["demo"], month)
            if data:
                Recap.objects.create(user=users["demo"], month=month, data=data)

    def _seed_trust(self, users, password):
        """A staff login for the moderation console and one open report to review."""
        from social.models import Report

        mod = User.objects.filter(username="mod").first()
        if mod is None:
            mod = create_account(
                email="mod@jingle.local",
                username="mod",
                password=password,
                display_name="Jingle Moderator",
                birth_year=1990,
            )
        if not mod.is_staff:
            mod.is_staff = True
            mod.save(update_fields=["is_staff"])
        if not Report.objects.filter(reporter=users["aanya"]).exists():
            Report.objects.create(
                reporter=users["aanya"],
                target_type="user",
                target_id=users["neel"].pk,
                reason="spam",
                details="Keeps sending the same song with a link in the note.",
            )

    def _seed_circles(self):
        """Two demo circles (Sprint 6): one the demo login owns, one it joined."""
        from circles.models import Circle, CircleMember, Role

        circles = (
            ("KJ Somaiya crew", "demo", ("aanya", "kabir", "dev", "ishaan")),
            ("Indie night", "zoya", ("demo", "meera", "neel")),
        )
        users = {
            u.username: u for u in User.objects.filter(username__in=[p.username for p in PERSONAS])
        }
        for name, owner, members in circles:
            if Circle.objects.filter(name=name, owner=users[owner]).exists():
                continue
            c = Circle.objects.create(name=name, owner=users[owner], member_count=1 + len(members))
            CircleMember.objects.create(circle=c, user=users[owner], role=Role.OWNER)
            for m in members:
                CircleMember.objects.create(circle=c, user=users[m], role=Role.MEMBER)


def _seed_circle_playlists() -> None:
    from jingle_common.demo import CATALOG, PERSONAS

    from circles import playlist
    from circles.models import Circle, CircleMember

    notes = [
        "for the late drive",
        "trust me on this one",
        "",
        "the chorus!!",
        "",
        "our fest anthem",
    ]
    favs = {p.username: p.favourites for p in PERSONAS}
    for c in Circle.objects.all():
        if c.playlist.exists():
            continue
        members = [m.user for m in CircleMember.objects.filter(circle=c).select_related("user")]
        added = 0
        for i, u in enumerate(m for m in members if m.username in favs):
            for j in range(2):
                if added >= 6:
                    break
                t = CATALOG[favs[u.username][(i * 2 + j) % len(favs[u.username])]]
                try:
                    playlist.add(
                        c, u, title=t.title, artist=t.artist, note=notes[added % len(notes)]
                    )
                    added += 1
                except Exception:  # noqa: BLE001 - duplicates or limits just skip
                    log.info("demo playlist song skipped")
