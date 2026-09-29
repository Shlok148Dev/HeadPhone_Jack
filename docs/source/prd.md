# Jingle — Product Requirements Document

Sep 29, 2026 · @Shlok

## 1. Executive summary

Jingle is the social layer music apps never built: one place where a
friend group split across Spotify, Apple Music, Amazon Music and YouTube
Music can see what each other is playing, share songs with a reason, and
meet every week over music.

**Thesis.** Music taste is already social: people text links, post
screenshots and argue in group chats. But every streaming app keeps its
social features inside its own walls, and none explains why two people
match. Jingle wins by being the only neutral, cross-platform,
explainable layer.

**What we ship first.** A web app (Release 2, public launch) where a
user connects a free ListenBrainz or Last.fm bridge, or Apple Music
directly, or imports YouTube Music. They add friends and join circles.
Then they get:

- a live activity feed that never fakes a Live badge

- recommendations that open on the friend's own platform

- Blends and live listening sessions with a voted queue

- an explained compatibility score

- a weekly song battle per circle and a monthly recap

**Why now, and the one hard constraint.** In February 2026 Spotify cut
new developer apps to 5 users and tied Extended Quota to registered
businesses with 250,000 monthly users. So direct Spotify integration
cannot carry a launch. Jingle's ingestion therefore runs through open
scrobbling bridges that already carry plays from every major platform.
That makes Jingle more neutral, not less capable.

**Targets for the first 6 months after launch:** 60,000 registered
users, 25,000 daily actives, 5,000 peak concurrent, and at least 40% of
weekly actives in a circle that ran a battle that week.

## 2. Problem, opportunity and competition

No product today lets a friend group on different streaming apps share
music socially and understand why they match; that gap is Jingle's
opportunity.

### 2.1 Problems

| \#  | Problem                                                                                         | What people do today                   |
|-----|-------------------------------------------------------------------------------------------------|----------------------------------------|
| P1  | Friend groups are split across platforms, and each app's social features stop at its own border | Paste links that open in the wrong app |
| P2  | Shared songs vanish into chat history; the sender never learns if it landed                     | Ask "did you listen?"                  |
| P3  | Taste matches are opaque numbers                                                                | Guess why two people click             |
| P4  | Music apps offer one big social moment a year (Wrapped)                                         | Nothing week to week                   |
| P5  | Seeing what friends play now is desktop-only or platform-locked                                 | Screenshots and stories                |

### 2.2 Opportunity

The open scrobbling ecosystem already moves plays from every major
platform into ListenBrainz and Last.fm. Scrobblers exist for Spotify,
Apple Music, YouTube Music and Amazon Music on web, Android and desktop.
Jingle turns that plumbing into a consumer social product. Its moat is
three things together: neutrality across platforms, explanations on
every match, and weekly rituals that bring circles back.

<img src="media/image1.png" style="width:6in;height:4.00893in"
alt="positioning · qualitative placement, not measured" />

positioning · qualitative placement, not measured

The top-right corner is empty: tools that cover every platform (Last.fm,
ListenBrainz) are solo-stats products, and the social ones stay inside
one or two platforms.

### 2.3 Competitor notes

| Product                             | Strength                            | Gap Jingle fills                                                      |
|-------------------------------------|-------------------------------------|-----------------------------------------------------------------------|
| Spotify Blend, Jam, Friend Activity | Deep inside Spotify                 | Spotify-only; Friend Activity is desktop-only; Blend reasons are thin |
| Apple Music shared profiles         | Built into Apple Music              | Apple-only; no rituals                                                |
| Airbuds                             | Widget-first social listening       | Two platforms; no explained compatibility; no circles or battles      |
| stats.fm, Receiptify                | Personal stats and shareable images | Solo; no friend graph                                                 |
| Last.fm, ListenBrainz               | Every platform through scrobbling   | Stats and history, little social depth; dated consumer UX             |

Placement in the map is our reading of each product's public features as
of September 2026, not a measurement.

## 3. Personas, jobs to be done, and habit loops

Four personas drive the design, and three loops (daily peek, weekly
battle, monthly recap) give each of them a reason to return.

### 3.1 Personas

| Persona              | Who                                                       | Platform mix                                      | Core job                               | Must not happen                       |
|----------------------|-----------------------------------------------------------|---------------------------------------------------|----------------------------------------|---------------------------------------|
| Aanya, the Connector | 20, college student in Mumbai; runs the friend group chat | Friends on Spotify, Apple Music and YouTube Music | "Keep my crew's music in one place"    | Friends left out because of their app |
| Kabir, the Curator   | 22, builds playlists for everyone                         | Spotify                                           | "Get credit when my picks land"        | Sends that vanish unheard             |
| Meera, the Lurker    | 19, rarely posts                                          | Apple Music                                       | "See what friends play without effort" | Being forced to post                  |
| Dev, the Competitor  | 21, loves leaderboards                                    | YouTube Music                                     | "Win the week with the best song"      | Rigged or dead battles                |

### 3.2 Jobs to be done

1.  When a friend is playing something, I want to see it and open it in
    my own app, so I can listen along without asking.

2.  When I find a song a friend will love, I want to send it with a
    reason and know they heard it.

3.  When my group hangs out, I want one queue everyone can add to and
    vote on.

4.  When I meet someone new, I want to see quickly and honestly how our
    tastes overlap.

5.  Every week, I want a light, fun reason to talk music with my circle.

6.  When I join, I want to find my people fast, even if none of my
    friends are on Jingle yet.

### 3.3 Habit loops

| Loop             | Trigger                                                 | Action                           | Reward                                | Investment                   |
|------------------|---------------------------------------------------------|----------------------------------|---------------------------------------|------------------------------|
| Daily peek       | Push: "3 friends are live" (at most 1 a day by default) | Open the Live shelf; tap a track | Hear what friends hear, in my own app | React or send a track        |
| Weekly battle    | Circle opens nominations Monday 18:00 IST               | Nominate one song; vote on 3     | Leaderboard reveal Sunday 21:00 IST   | Season points; circle banter |
| Monthly recap    | Recap ready on the 1st                                  | View and share the card          | Identity, comparison with friends     | Taste timeline grows         |
| Discovery credit | "Your pick is now in Ria's top artists"                 | Open Ria's profile               | Status as the friend with taste       | Send more                    |

Notification defaults follow EP-11: at most 5 pushes a day, quiet hours
23:00–08:00, each type switchable.

## 4. Goals, non-goals and success metrics

The north-star metric is **Weekly Shared Moments**: weekly active users
who had at least one two-sided music interaction, targeted at 50% of
weekly actives six months after launch.

### 4.1 Goals

1.  Make a mixed-platform friend group feel like one group within its
    first 5 minutes.

2.  Make every recommendation and match explainable.

3.  Create a weekly habit through circles and battles, not through
    notification volume.

4.  Run reliably at 5,000 concurrent users on a student-scale budget.

5.  Stay inside every platform's terms and India's DPDP rules from day
    one.

### 4.2 Non-goals for Releases 1–2

- Streaming, hosting or downloading audio

- A music catalogue or search engine of Jingle's own

- Payments, ads or creator monetisation

- Direct messaging beyond short threads on shared tracks

- Forcing playback on another person's device

- Any unofficial or scraped API

### 4.3 Metrics and targets (6 months after public launch)

| Metric                             | Definition                                                                                                                 | Target  |
|------------------------------------|----------------------------------------------------------------------------------------------------------------------------|---------|
| Weekly Shared Moments (north star) | Share of weekly actives with ≥ 1 two-sided interaction: a send that was played, a session with 2+ people, or a battle vote | 50%     |
| Activation                         | New users who link a source and have 1 accepted friend within 7 days                                                       | 60%     |
| Time to first friend               | Median from sign-up to first accepted friend                                                                               | ≤ 24 h  |
| Suggestion acceptance              | Accepted ÷ shown suggestions (after dedup)                                                                                 | ≥ 8%    |
| Send play-through                  | Played ÷ delivered recommendations                                                                                         | ≥ 35%   |
| Circle battle participation        | Circle members who nominate or vote in a week                                                                              | ≥ 40%   |
| D30 retention                      | Users active on day 30 after sign-up                                                                                       | ≥ 25%   |
| Live coverage                      | Friends' cards that are Live or Recent (not Top only) at peak hour                                                         | ≥ 60%   |
| False-Live incidents               | Cards shown Live without a valid signal                                                                                    | 0       |
| Crash-free sessions                | Web and mobile                                                                                                             | ≥ 99.5% |

### 4.4 Guardrails

- Push opt-out rate stays under 10% per month; if it rises, notification
  volume drops before anything else changes.

- Block and report rate stays under 1% of friendships; above it,
  suggestions are paused for review.

- Any metric gain that raises either guardrail is rolled back.

## 5. Feature specifications

Eleven features ship by public launch; each spec below states behaviour,
edge cases and the metric that proves it works, and the SRS story IDs
are the build contract.

### 5.1 Onboarding and source linking (EP-01)

Four steps, each skippable except the first: **Profile → Sources →
Privacy → Friends.**

- The Sources step asks "Which app do you use most?" and then shows the
  best path for that app:

| User's main app | Recommended path                                                                                     | What they get                              |
|-----------------|------------------------------------------------------------------------------------------------------|--------------------------------------------|
| Spotify         | Connect Spotify to ListenBrainz or Last.fm in 2 taps (guided), then connect that bridge to Jingle    | Live, Recent, Top                          |
| Apple Music     | Connect Apple Music (MusicKit), plus a scrobbler app for Live                                        | Recent, heavy rotation; Live via scrobbler |
| YouTube Music   | Web Scrobbler extension or Pano Scrobbler (Android) to ListenBrainz; plus Takeout import for history | Live via scrobbler; history from export    |
| Amazon Music    | Scrobbler to a bridge today; direct link when Amazon approves                                        | Live via scrobbler                         |

- Each path shows a progress check: "We've seen your first play ✓".

- Metric: 70% of sign-ups finish the Sources step with at least one
  working source.

### 5.2 Friend suggestions (EP-03)

**What the user sees.** A "People you may know" row on Home and a full
list under Friends: up to 20 people, each with a photo, name and up to 3
reasons, and Add or Dismiss buttons.

**Where suggestions come from**, blended into one ranked list:

| Signal                                                    | Example reason shown                        | Weight at launch |
|-----------------------------------------------------------|---------------------------------------------|------------------|
| Mutual friends (friends of friends, Adamic–Adar weighted) | "4 mutual friends"                          | 0.35             |
| Taste similarity (artist and genre embeddings)            | "Both love Kendrick Lamar and Arijit Singh" | 0.30             |
| Shared context: same circle, session, battle or concert   | "Voted in the same battle"                  | 0.15             |
| Contacts (opt-in, hashed on device)                       | "In your contacts"                          | 0.10             |
| Same college or city (opt-in profile fields)              | "Also at KJ Somaiya"                        | 0.10             |

Weights start as a hand-tuned heuristic and move to a learned ranker
once 10,000 labelled accept/dismiss events exist.

**Rules.** Never suggest: blocked people, people who turned
discoverability off, anyone dismissed in the last 90 days, or (once
minors are allowed) adults to minors and minors to adults. Reasons never
reveal listening data from someone in Private mode. At most 30 friend
requests a day per user.

**Cold start.** With no friends and no taste data yet: show an invite
link and QR, "taste twins" computed from the onboarding genre picker,
and public circles at the user's college.

**Metric.** Acceptance of shown suggestions ≥ 8%; median time to first
friend ≤ 24 h.

### 5.3 Friend circles (EP-04)

**What it is.** A named group of up to 50 members (for example "College
hip-hop crew") with its own feed, Blend, live sessions and weekly
battle. A user can be in up to 20 circles.

| Aspect            | Behaviour                                                                                                                                               |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| Roles             | Owner (one), Admins, Members                                                                                                                            |
| Joining           | Invite from a friend, or an invite link that expires in 7 days; admins can require approval                                                             |
| Visibility        | Private (default, invite only) or Discoverable (appears in suggestions for people at the same college)                                                  |
| Circle page       | Live shelf of members, circle feed, current battle, circle Blend, taste map                                                                             |
| Suggested circles | Jingle detects tight clusters of friends with shared taste and suggests "Make a circle with these 5?" to one of them; nobody is added without accepting |
| Leaving           | Anyone can leave; admins can remove; the owner must hand over ownership first                                                                           |

**Metric.** 50% of activated users join or create a circle within 14
days.

### 5.4 Activity feed (EP-05)

- Top: "Live now" horizontal shelf. Then friend cards sorted Live →
  Recent (newest first) → Top.

- Every card names its source and route, for example "Live on Apple
  Music via ListenBrainz".

- Filter chips: All, each circle, Live only.

- Tap a track: open in *my* app, send, react, or start a Blend with that
  friend.

- Degraded state: when a bridge is down, cards keep their last state
  with the true time and a small "delayed" tag.

### 5.5 Recommendations and mixtapes (EP-06)

Send one track or a 5–8 track mixtape with a note of up to 280
characters. The recipient opens it on their own platform through the
cross-platform Recording link. The sender sees Sent → Delivered → Viewed
→ Played; "Played" is confirmed when the recipient's bridge reports the
track within 7 days. Discovery credit fires when the sent artist enters
the recipient's monthly top 20.

### 5.6 Blends (EP-07)

A Blend of 2–6 people or a circle: 30 tracks, balanced so no member
supplies more than 40%, each with a one-line reason ("Both of you played
this in the last month"). Regenerate keeps pinned tracks. Save to Apple
Music or Spotify as a playlist where the API and terms allow.

### 5.7 Live sessions (EP-07)

A host starts a session and invites friends or a circle. Each member
plays on their own app; Jingle keeps the shared queue, votes and chat in
sync. Members can add anonymously. If the host leaves, the next member
to join becomes host. Maximum 50 members per session.

### 5.8 Compatibility and analytics (EP-08)

Score 0–100 with at most 3 reasons, shared artists and genres, and a
sound comparison (tempo, energy, mood) only when Jingle has analysed
preview audio for both people. Otherwise the card says "Sound comparison
unavailable". The taste timeline shows genre shares month by month for
12 months.

### 5.9 Rituals (EP-09)

**Weekly song battle, per circle:** nominations Monday 18:00 → Friday
18:00 IST; voting Friday 18:00 → Sunday 21:00 IST; leaderboard within 5
minutes of close. One nomination and 3 votes per member, never on one's
own song. An 8-week season table crowns a champion.

**Monthly recap:** a 9:16 card generated by the 2nd of each month:
minutes, top 5 tracks, top genre shift, top friend match, platforms
used. Shareable as an image or link.

### 5.10 Concerts (EP-10)

Alerts for shows within a chosen radius (default 50 km) by artists the
user shares with at least one friend. "Going" is private unless turned
on.

### 5.11 Notifications (EP-11)

In-app always; push opt-in; weekly email digest optional. Defaults: at
most 5 pushes a day, quiet hours 23:00–08:00, one "friends are live"
push a day at most.

## 6. UX principles, key flows and design direction

Jingle should feel as familiar as Spotify on first open (sidebar,
shelves, a bottom now-playing bar) while its own identity comes from the
violet-to-cyan palette, the Blip mascot and honest, explained social
cards.

### 6.1 Principles

1.  **The user is in control.** Every sharing setting is visible,
    reversible and one tap away; nothing is shared or joined without
    consent.

2.  **Honest over impressive.** A card that says "2 h ago" beats a fake
    Live badge.

3.  **Explain everything.** Scores, suggestions and Blend tracks always
    carry their reason.

4.  **Their app, not ours.** Every track opens on the viewer's own
    platform.

5.  **Calm by default.** Few notifications, motion that respects
    reduced-motion settings, dark theme default with a light toggle.

6.  **Every state designed.** Default, loading (content-shaped
    skeletons), empty (with Blip and one clear action), error and
    degraded.

### 6.2 Key flows

**First run (target: populated feed in ≤ 5 minutes)**

1.  Landing → "Connect your music"

2.  Sign up with Google, Apple or email

3.  Pick main app → guided source path → "first play seen ✓"

4.  Privacy: who sees my activity; discoverability on or off

5.  Find friends: suggestions, invite link, QR, optional contacts

6.  Home feed with a Live shelf, or Blip's empty state pointing to
    invites

**Send a song:** feed card → Send → pick friends or a circle → optional
note → sent; status chips update live.

**Weekly battle:** Monday push → circle page → Nominate (search any
platform) → Friday push → vote on 3 → Sunday reveal with an animated
podium.

**Start a session:** circle page → Start session → members join from
push → shared queue with votes → each member plays on their own app.

### 6.3 Design direction

| Element        | Decision                                                                                                                                                                            |
|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Layout         | Spotify-style shell: left sidebar (Home, Friends, Circles, Blends, Rituals, Profile), main canvas of horizontal shelves, persistent bottom bar with *my* now-playing and quick Send |
| Theme          | Dark default (#08080B base), light theme toggle in the top bar; both meet 4.5:1 text contrast                                                                                       |
| Colour         | Violet \#8B6BFF → cyan \#3FE7D8 gradient for brand and primary actions; coral \#FF6B5E reserved for Live                                                                            |
| Type           | Bricolage Grotesque for display, Inter for UI, JetBrains Mono for data labels                                                                                                       |
| Artwork        | Real cover art from Apple Music, Spotify (with attribution) or Cover Art Archive; a generative cover pattern only when none exists                                                  |
| Platform marks | Official platform logos used only as their brand guidelines allow; otherwise text badges                                                                                            |
| Mascot         | Blip, an SVG character with idle, wave, cheer and sleepy poses for empty and success states                                                                                         |
| Motion         | Framer Motion springs for card entry, live equaliser bars, podium reveal; all disabled under prefers-reduced-motion                                                                 |

Build order follows the design-system-first practice: a /design route
with tokens, type scale and every card variant is built and reviewed
before feature screens.

## 7. Platform strategy and API access realities

Jingle launches bridge-first: ListenBrainz and Last.fm carry Live and
Recent data from all four platforms, Apple Music is linked directly, and
direct Spotify and Amazon links stay gated until their owners open
access.

**Spotify first.** Spotify is the platform Jingle was born from, and
Spotify listeners get the most complete support: Spotify's built-in
Last.fm scrobbling on every device, direct push from Android and desktop
scrobblers to Jingle, and a direct Spotify link ready to switch on the
day Extended Quota is granted. The Last.fm commercial agreement and the
company registration that Extended Quota needs are therefore Sprint 1
actions (Development Plan, Section 4). Every other platform then plugs
into the same push and bridge paths, so all four platforms get the full
product.

**Invisible to the user.** None of these paths is a user chore. The user
presses "Connect Spotify" once; Jingle's Connection Orchestrator picks
the route, the Jingle Android app and browser extension capture
listening themselves, and cards only ever say "Live on Spotify". Full
design: Technical Bible, section 2.5.

### 7.1 Per-platform strategy

| Platform      | Launch path                                             | Direct API status (Sept 2026)                                                                                                                                                                                                                                                                                                                                           | Upgrade trigger                                                               |
|---------------|---------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| Spotify       | Spotify → ListenBrainz or Last.fm → Jingle              | New Development Mode apps: 5 users, owner needs Premium; Extended Quota needs a registered business and 250,000 MAU ([migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide), [TechCrunch](https://techcrunch.com/2026/02/06/spotify-changes-developer-mode-api-to-require-premium-accounts-limits-test-users/)) | Register a company, pass 250,000 MAU, and get written clarity on Policy III.5 |
| Apple Music   | MusicKit direct link, plus a scrobbler for Live         | Open with an Apple Developer Program membership; no now-playing endpoint                                                                                                                                                                                                                                                                                                | Already live                                                                  |
| Amazon Music  | Scrobbler → bridge                                      | Web API V2 is a closed beta for approved developers ([Amazon](https://developer.amazon.com/docs/music/API_web_overview_v2.html))                                                                                                                                                                                                                                        | Amazon approves access                                                        |
| YouTube Music | Scrobbler → bridge for Live; Takeout upload for history | No personal-history API; Data Portability API scope myactivity.youtube is Restricted ([Google](https://developers.google.com/data-portability/user-guide/scopes))                                                                                                                                                                                                       | Google verifies Jingle for the restricted scope                               |

### 7.2 Why bridge-first is a strength

- **Neutral.** One integration covers every player that scrobbles,
  including future platforms.

- **Live everywhere.** Both bridges report now-playing, so Apple Music
  and YouTube Music friends can appear Live, which no direct API allows.

- **Clean data rights.** ListenBrainz data is openly licensed, so
  Jingle's models can train on it without breaching Spotify Policy
  III.14.

- **User-owned.** Users already own their scrobble history; switching
  platforms does not reset their taste profile.

### 7.3 Terms we design around

| Term                                                                                                               | Product consequence                                                                                                              |
|--------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| Spotify Policy III.5: no product integrated with content from another service                                      | Direct Spotify data is shown only in a Spotify-attributed panel for allowlisted testers until Spotify confirms otherwise         |
| Spotify Policy III.14: no ML training on Spotify content                                                           | Models never train on direct-Spotify data                                                                                        |
| Last.fm terms: non-commercial by default; 100 MB cap; AudioScrobbler credit ([terms](https://www.last.fm/api/tos)) | Last.fm is used for live display; ListenBrainz is preferred for storage and training; seek a commercial agreement before revenue |
| Platform branding guidelines                                                                                       | Official marks only where permitted, with attribution and link-back                                                              |

### 7.4 The user-facing promise

"Jingle works with whatever you listen on. For live status, connect a
free scrobbler; for history, link or import your app." Onboarding makes
that a 2-minute guided step rather than a technical chore.

## 8. Release plan, go-to-market, risks and open questions

Jingle opens a 100-person closed beta on 11 January 2027 and launches
publicly on 14 March 2027, seeded college by college; the sprint-level
schedule lives in the Development Plan.

### 8.1 Releases

- **R0 Foundations (5 Oct – 1 Nov 2026):** accounts, ListenBrainz
  bridge, empty feed, CI/CD, observability.

- **R1 Closed beta (opens 11 Jan 2027):** EP-01 to EP-06 at Must level
  for 100 invited users across 5 circles.

- **R2 Public launch (14 Mar 2027):** Blends, sessions, compatibility,
  battles, recap, concerts, moderation; load test passed at 5,000
  concurrent users.

- **R3 Growth (from 22 Mar 2027):** mobile apps, Should and Could
  stories, Amazon Music if approved, learned suggestion ranker.

Between R0 and R1 sits a **10-user web pilot** that needs no approval
from any company (Spotify via 5 direct slots and Spotify's Last.fm link;
every platform via the Jingle Companion browser extension). Releases 0.5
to 2 are web only; mobile apps and store publishing are Release 3.

### 8.2 Go-to-market

| Stage           | Tactic                                                                                 | Target                               |
|-----------------|----------------------------------------------------------------------------------------|--------------------------------------|
| Seed            | Beta with 5 real friend circles at KJ Somaiya; weekly battles run by circle admins     | 100 users, 30% 7-day retention       |
| Campus launch   | Circle-vs-circle battle between college clubs; QR invites at fests                     | 5,000 users in Mumbai colleges       |
| Viral loop      | Monthly recap cards and battle podiums shared to Instagram stories with an invite link | Each recap share brings 0.3 sign-ups |
| Creator circles | Student DJs and campus radio run public circles                                        | 20 public circles                    |
| Expansion       | Other Indian metro colleges, then global English-speaking campuses                     | 60,000 registered by September 2027  |

### 8.3 Risks

| Risk                                            | Likelihood | Impact | Response                                                                            |
|-------------------------------------------------|------------|--------|-------------------------------------------------------------------------------------|
| Users find scrobbler setup too hard             | Medium     | High   | Guided 2-tap flows per app; video help; track setup completion weekly               |
| Last.fm or ListenBrainz changes terms or limits | Low        | High   | Support both; seek Last.fm commercial agreement; cache within terms                 |
| Spotify objects to any Spotify display          | Low        | Medium | Direct Spotify stays allowlist-only and attributed; bridges carry Spotify listeners |
| Cold start: no friends on Jingle yet            | High       | High   | Taste twins, college circles, invite rewards, recap sharing                         |
| Harassment or spam through requests             | Medium     | High   | Request limits, block, report, moderation queue, suggestion guardrails              |
| Student team capacity during exams              | High       | Medium | Lighter sprints planned in December; scope by MoSCoW                                |
| Hosting cost above budget                       | Medium     | Medium | Student cloud credits; autoscaling floors; cost alerts                              |

### 8.4 Open questions

- [ ] Launch 18+ only, or ship the parental-consent flow for under-18
  students in R1?

- [ ] Keep a Spotify panel for allowlisted testers, or rely only on
  bridges until Spotify replies?

- [ ] Should battle schedules be fixed in IST or set per circle time
  zone from R3?

- [ ] Is 50 the right circle cap, or should verified campus circles go
  to 200?
