# Jingle — Software Requirements Specification v4.0 (Agile/Scrum)

Sep 29, 2026 · @Shlok

## 1. Introduction

Jingle v4.0 is specified as a production service for 1,000–5,000 concurrent users, built with Agile Scrum, and re-architected around what each music platform actually allows in 2026.

### 1.1 Purpose

This SRS defines what Jingle must do and how well it must do it. It is the reference for the Product Owner, developers, testers and evaluators. It is also the seed of the Scrum product backlog: every functional requirement is a user story with testable acceptance criteria.

### 1.2 Scope

Jingle is a cross-platform social layer for music listening. It reads a user's listening activity from Spotify, Apple Music, Amazon Music and YouTube Music, directly or through open scrobbling bridges. It turns that activity into shared, explained experiences between friends.

In scope for v4.0:

- Account creation and linking of one or more listening sources
- Friend graph, friend suggestions and friend circles
- Live / Recent / Top-Tracks activity feed with honest freshness labels
- Recommendations and mixtapes with delivery tracking
- Blends and live group listening sessions
- Explained taste compatibility and taste-evolution analytics
- Weekly song battles per circle and a monthly recap
- Concert alerts, notifications, admin and moderation tools

Out of scope: streaming or hosting audio, a music catalogue of its own, payments, and any use of unofficial or scraped platform APIs.

### 1.3 What changed from v3.0, and why

Three platform facts verified on 2026-09-29 force changes to the v3.0 design:

| Fact | Source | Consequence for Jingle |
| --- | --- | --- |
| New Spotify Development Mode apps are capped at 5 users, and the owner needs Premium (from 11 Feb 2026) | [Spotify migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide) | Direct Spotify OAuth cannot serve 1,000+ users |
| Extended Quota requires a legally registered business with at least 250,000 MAU | [TechCrunch, 6 Feb 2026](https://techcrunch.com/2026/02/06/spotify-changes-developer-mode-api-to-require-premium-accounts-limits-test-users/) | Spotify at scale must come through a bridge until those bars are met |
| Spotify Developer Policy III.5 bars products "integrated with streams or content from another service"; III.14 bars training ML models on Spotify content | [Spotify Developer Policy](https://developer.spotify.com/policy) | Spotify API data is display-only and isolated; models train on bridge and Jingle-native data |

The answer is a tiered ingestion model (Section 4). Open scrobbling bridges, ListenBrainz and Last.fm, become the primary path at scale. Official APIs are used where their terms and quotas allow.

### 1.4 Intended audience

| Reader | Read first |
| --- | --- |
| Product Owner | Sections 3, 6, 8 |
| Developers | Sections 4, 5, 6, 7 |
| Testers | Acceptance criteria in Section 6; Section 7 targets |
| Evaluators | Sections 1, 3, 8 (traceability) |

### 1.5 Conventions

| Item | Format | Example |
| --- | --- | --- |
| Epic | EP-nn | EP-03 Friend suggestions |
| User story | JNG-\<epic>-\<nn> | JNG-03-04 |
| Non-functional requirement | NFR-\<area>-\<nn>, areas PERF, SCAL, AVAIL, SEC, PRIV, A11Y, OBS | NFR-PERF-02 |
| Business rule | BR-nn | BR-01 No false Live |
| Priority | MoSCoW: Must, Should, Could, Won't (this release) | Must |
| Acceptance criteria | Gherkin: Given / When / Then | See Section 6 |

"Shall" marks a binding requirement. Every threshold is a number, so every requirement can be tested as written. Thresholds still open are listed in Section 8.

### 1.6 References

- ISO/IEC/IEEE 29148:2018, Requirements engineering; IEEE Std 830-1998
- The Scrum Guide, November 2020 edition
- Digital Personal Data Protection Act 2023 and DPDP Rules 2025, notified 13 Nov 2025 ([timeline summary](https://www.sansalegal.com/post/dpdp-act-2023-and-rules-2025-phased-implementation-timeline-and-business-compliance-deadlines))
- Platform documentation: Spotify Web API, Apple Music API, Amazon Music Web API, Google Data Portability API, Last.fm API, ListenBrainz API
- Jingle PRD, Technical Bible, Technology Stack and Development Plan (companion documents)

### 1.7 Revision history

| Version | Change |
| --- | --- |
| 4.0 | Agile/Scrum structure; tiered ingestion after 2026 Spotify changes; friend suggestions and circles; scale to 5,000 concurrent users; DPDP Rules 2025 |
| 3.0 | Multi-platform scope; 129 atomic requirements; Source Adapter pattern |
| 2.1 | Review pass: quantified vague terms, fixed a forward reference |
| 2.0 | Atomic requirements, timing and exception subsections |
| 1.0 | First IEEE 830 structure, Spotify only |

## 2. Overall description

Jingle is a new, self-contained web product (mobile apps follow) that depends on external music platforms for all listening data and never touches audio.

### 2.1 Product perspective

Jingle sits between its users and up to five listening sources. A Source Adapter layer normalises every source into one internal event and feed-card contract, so Feed, Blend, Analytics and Social features never branch on platform. The companion Technical Bible defines the services; the Technology Stack document names the tools.

### 2.2 Product functions

| Epic | Function |
| --- | --- |
| EP-01 | Sign up, sign in, link and unlink listening sources |
| EP-02 | Send, accept, decline, revoke and block friend connections |
| EP-03 | Suggest people the user may know or share taste with, with reasons |
| EP-04 | Create and manage friend circles; suggest taste circles |
| EP-05 | Show each friend's Live, Recent or Top-Tracks state, honestly labelled |
| EP-06 | Send tracks and mixtapes; track Sent, Delivered, Viewed, Played |
| EP-07 | Generate explained Blends; run live sessions with a voted queue |
| EP-08 | Explain compatibility; chart taste evolution over 12 months |
| EP-09 | Run a weekly song battle per circle; generate a monthly recap |
| EP-10 | Alert users to shows for artists they share with friends |
| EP-11 | Deliver in-app, push and email notifications |
| EP-12 | Moderate content, manage abuse reports, manage API budgets and feature flags |
| EP-13 | Meet the scale, security, privacy and observability targets |

### 2.3 User classes

| Class | Description | Expected skill |
| --- | --- | --- |
| Member | Links at least one source and uses the full product at that source's capability level | Any consumer social-app user |
| Import-only member | Has only a YouTube Music export or a manual list; no live features | Can follow a 4-step export guide |
| Bridged friend | Represented by a list a member imported; has no Jingle account | None |
| Circle admin | A member who owns or administers a circle | Member skills |
| Moderator | Staff who review reports and enforce community rules | Trained on the moderation console |
| Platform admin | Staff who manage feature flags, API budgets and incidents | Engineering |

### 2.4 Operating environment

- Web client: the latest two major versions of Chrome, Safari, Firefox and Edge; viewport widths 360–1920 px
- Mobile (Release 3): iOS 17+ and Android 12+ through React Native
- Servers: Linux containers on managed Kubernetes in an India region (ap-south-1 or equivalent), with a CDN at the edge
- External services: Spotify Web API, Apple Music API, Amazon Music Web API (when approved), Google Data Portability API, Last.fm API, ListenBrainz API, MusicBrainz and Cover Art Archive, Ticketmaster Discovery API, Firebase Cloud Messaging

### 2.5 Design and implementation constraints

| ID | Constraint |
| --- | --- |
| C-01 | No platform pushes playback events; live state must be polled within each source's rate limits |
| C-02 | A new Spotify Development Mode app serves at most 5 users; Extended Quota needs a registered business and 250,000 MAU |
| C-03 | Spotify API content may not be combined into a multi-service product (Policy III.5) or used to train models (III.14); it is isolated and display-only |
| C-04 | Apple Music and Amazon Music expose no now-playing endpoint |
| C-05 | Amazon Music Web API V2 is a closed beta for approved developers only |
| C-06 | YouTube Music has no official personal-history API; history arrives by Takeout upload or the Data Portability API (restricted scope, Google verification) |
| C-07 | Last.fm data is non-commercial unless a commercial agreement is signed; 100 MB storage cap; "powered by AudioScrobbler" credit |
| C-08 | Spotify's audio-features, audio-analysis and recommendations endpoints are unavailable to apps created after 27 Nov 2024; batch track fetch and search limits were cut in Feb 2026 |
| C-09 | Personal data processing follows the DPDP Act 2023 and Rules 2025; full obligations apply from 13 May 2027, and Jingle adopts them at launch |

### 2.6 Assumptions and dependencies

- A-01: Users who want Live status across platforms are willing to connect a free ListenBrainz or Last.fm account, or already have one.
- A-02: ListenBrainz and Last.fm stay available with their current public endpoints.
- A-03: Apple Music members hold an active subscription with Listening History enabled.
- A-04: Planning load is 60,000 registered users, 25,000 daily actives and 5,000 peak concurrent users. These are sizing assumptions, not forecasts.
- A-05: The team is 3 developers plus AI-assisted development, working in 2-week sprints.

### 2.7 Initial state

A new account starts with no linked sources, no friends and no circles. Default privacy: activity visible to friends only; precise last-active time visible to friends; discoverable in suggestions only after the user opts in during onboarding; concert attendance private. Feed, suggestions and analytics show their named empty states (JNG-05-08, JNG-03-07, JNG-08-06) until data exists.

## 3. Agile/Scrum requirements process

This SRS is a living document: Section 6 is the product backlog at release planning, and it changes only through backlog refinement and sprint review.

### 3.1 How the SRS maps to Scrum artefacts

| ISO/IEC/IEEE 29148 element | Scrum artefact | Where it lives |
| --- | --- | --- |
| Stakeholder needs | Product Goal and epics | PRD; Section 2.2 |
| System functional requirements | User stories with acceptance criteria | Section 6; backlog tool |
| Non-functional requirements | Constraints applied to every story; part of the Definition of Done | Section 7 |
| Verification | Gherkin scenarios become automated tests | Section 6; test suite |
| Traceability | Story → test → pull request → release | Section 8.3; issue links |

Product Goal: *"By the end of Release 2, a friend group spread across four music platforms can see each other's listening, share music with reasons, and play a weekly battle, for up to 5,000 people online at once."*

### 3.2 Story standard

Every story follows *As a \<user class>, I want \<capability>, so that \<outcome>* and meets INVEST: Independent, Negotiable, Valuable, Estimable, Small (fits one sprint), Testable. Stories carry a MoSCoW priority and a Fibonacci story-point estimate set in refinement, not in this document.

### 3.3 Definition of Ready

A story may enter a sprint only when all of these hold:

- [ ] It meets INVEST and fits in one 2-week sprint
- [ ] Acceptance criteria are written in Gherkin, including at least one failure path
- [ ] Affected NFRs are named (Section 7)
- [ ] External dependencies (platform approval, API key) are resolved or stubbed
- [ ] UX states are designed: default, loading, empty, error, and dark and light themes
- [ ] The team has estimated it

### 3.4 Definition of Done

A story is done only when all of these hold:

- [ ] Code is reviewed and merged to main; CI is green
- [ ] Every Gherkin scenario passes as an automated test
- [ ] Unit coverage of the changed code is at least 80%
- [ ] API changes are reflected in the OpenAPI schema; adapter changes pass contract tests
- [ ] The feature is behind a feature flag if it depends on an external approval
- [ ] Logs, metrics and traces exist for the new path (NFR-OBS)
- [ ] Accessibility checks pass with zero WCAG 2.2 AA violations from automated scans
- [ ] Privacy review is done if the story touches personal data
- [ ] Deployed to staging and accepted by the Product Owner

### 3.5 Change control

1. Anyone may propose a change as a backlog item.
2. The Product Owner orders the backlog; the team refines items one sprint ahead.
3. Scope inside a running sprint changes only if the Sprint Goal is at risk, by agreement of the Product Owner and developers.
4. Accepted changes update this SRS at sprint review, with a revision entry and the affected story IDs.
5. A change that alters a business rule (BR) or an NFR target needs a written rationale in Section 8.

### 3.6 Releases

| Release | Content | Gate |
| --- | --- | --- |
| R0 Foundations | Accounts, Jingle Connect, push ingestion, empty feed, CI/CD, observability | Staging stable 7 days |
| R0.5 Web pilot | Web app only, about 10 users, zero company approvals: Spotify via 5 direct slots plus Spotify's Last.fm link; all four platforms via the Jingle Companion browser extension; Apple, Amazon and Google integrations built but flagged off | Every pilot user reaches a populated feed; zero false-Live incidents |
| R1 Closed beta | EP-01 to EP-06 at Must level; 100 invited users; still web only | 7-day retention of 30% or more among beta users |
| R2 Public web launch | EP-07 to EP-12 at Must level; load test passed at 5,000 concurrent | All Must NFRs met |
| R3 Mobile and stores | Android app (Jingle Companion on the phone), then iOS; Play Store and App Store; approval-gated integrations switched on as approvals arrive | Store approval |

**Web phase scope.** Until R3, Jingle is a web app. A browser cannot see what other phone apps play, so in R0.5–R2 phone listening on YouTube Music, Apple Music and Amazon Music shows Recent and history only, never Live. Spotify listeners get Live on every device through Spotify's Last.fm link.

## 4. Listening Source Model

Jingle reads listening data through three tiers, and at 5,000 concurrent users the open bridges (Tier A) carry most of it, because no direct platform API is open to a new app at that scale.

**Spotify is Jingle's core platform.** Spotify listeners get three complete paths, each giving Live, Recent and Top: Spotify's built-in Last.fm scrobbling (works on every device, iPhone included), push from Android or desktop scrobblers straight to Jingle (Section 4.0), and a direct Spotify link that is built and tested with 5 testers and switched on for everyone once Extended Quota is granted. Apple Music, Amazon Music and YouTube Music listeners use the same push and bridge paths plus their own direct links, so all four platforms get the full product.

### 4.0 Push ingestion (primary Live path)

Jingle exposes a ListenBrainz-compatible scrobble endpoint (`/ingest/1/submit-listens`, `/ingest/1/playing-now`) with a per-user token. Scrobbler apps that allow a custom ListenBrainz endpoint (Web Scrobbler in the browser, Pano Scrobbler on Android) send plays straight to Jingle: Live within seconds, with no third-party rate limit. Jingle can relay each scrobble on to the user's own ListenBrainz or Last.fm account. Push is the primary Live path at scale; polling bridges is the fallback.

### 4.0b Seamless connection (binding)

- BR-13 **One button per platform.** The user connects with a single "Connect Spotify" (or Apple Music, YouTube Music, Amazon Music) action. Jingle's Connection Orchestrator chooses the route (direct API, Jingle Companion, or bridge) and switches routes automatically; the user never picks or sees a route.
- BR-14 **No route words in the product.** Feed cards, profiles and notifications name only the music platform ("Live on Spotify"). Routes are internal; required third-party credits live on Settings → Connections.
- BR-15 **Feature parity by capability.** Features request capabilities, not routes; a missing capability gets a defined fallback, never an error or a setup prompt on a card.
- The only unavoidable steps are each platform's own consent screen and, on iPhone without direct access, one extra confirm; each is kept to one screen inside Jingle's flow.

JNG-01-14 (Must): As a Spotify listener on any device, I want to connect with one button and have everything work, so that I never deal with how Jingle gets my listening.

### 4.1 Ingestion tiers

| Tier | Sources | Role | Why |
| --- | --- | --- | --- |
| A — Open bridges | ListenBrainz, Last.fm | Primary path for Live and Recent on every platform | Both expose a now-playing signal; users can scrobble from Spotify, Apple Music, YouTube Music and Amazon Music through official integrations and scrobbler apps |
| B — Direct official APIs | Apple Music (MusicKit), Spotify Web API, Amazon Music Web API | Enrichment: recently played, heavy rotation, playlist export | Richer data, but quotas, closed betas and policy limit reach |
| C — User exports | Google Takeout upload; Google Data Portability API | YouTube Music history and top tracks | No official YouTube Music personal-history API exists |

### 4.2 Capability matrix (verified 2026-09-29)

| Source | Link method | Live | Recent | Top tracks | Playlist write | Reach limit | Key terms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ListenBrainz](https://listenbrainz.readthedocs.io/en/latest/users/api/core.html) | User token | Yes, `playing-now` | Yes, up to 1,000 per call | Yes, stats endpoints | Jingle-side only | None published | Open data; attribution |
| [Last.fm](https://www.last.fm/api/show/user.getRecentTracks) | Username (public) or web auth | Yes, `nowplaying="true"` | Yes, up to 200 per page | Yes | No | Rate limits enforced | [Non-commercial unless agreement; 100 MB cap; credit](https://www.last.fm/api/tos) |
| Apple Music | MusicKit user token (web, iOS, Android) | No | Yes, recent played tracks | Heavy rotation | Yes | None per user | Apple Developer Program membership |
| Spotify | OAuth 2.0 PKCE | Yes | Yes, 50 per call | Yes | Yes | 5 users in Development Mode; Extended Quota at 250,000 MAU | Policy III.5, III.9, III.14; attribution and link-back |
| [Amazon Music](https://developer.amazon.com/docs/music/API_web_overview_v2.html) | Login with Amazon | No | Not documented in V2 overview | Not documented | Library and playlists | Closed beta, approved developers only | Business-development approval |
| YouTube Music | Takeout upload or Data Portability API | No | Snapshot only | Derived from export | No | Data Portability scope is Restricted; Google must approve the app | Export dated; never live |

### 4.3 Link paths offered to users

1. **Connect ListenBrainz or Last.fm** (recommended, shown first). Gives Live and Recent for whatever the user plays, on any platform, once their player scrobbles.
2. **Connect Apple Music** through MusicKit. Adds recent plays and heavy rotation; never Live.
3. **Connect Spotify directly.** Available only to the 5 allowlisted Development Mode testers until Extended Quota is granted. Every other Spotify user is guided to connect Spotify to ListenBrainz or Last.fm.
4. **Connect Amazon Music.** Hidden behind feature flag `amazon_music_enabled` until Amazon approves access.
5. **Import YouTube Music.** Upload a Takeout `watch-history.json`, or authorise the Data Portability API once Google verifies Jingle.

### 4.4 Cross-platform track identity

Every listen resolves to a canonical `Recording` so a Spotify listener and an Apple Music listener can share a song:

1. Match by ISRC when the source gives one (Apple Music, Spotify).
2. Else match by MusicBrainz recording MBID (ListenBrainz and Last.fm often carry it).
3. Else fuzzy-match normalised artist and title strings against MusicBrainz, accepting a score of 90 or more out of 100; YouTube titles are cleaned of suffixes such as "(Official Video)".
4. Below the threshold, keep the listen as `unresolved`: it shows in the feed as plain text and is excluded from Blends and compatibility.
5. Store per-platform links on the Recording so "Open in my app" deep-links each friend to their own platform.

### 4.5 Resolution and data-use rules

- BR-01 **No false Live.** A Live state requires a now-playing signal less than 90 seconds old from a live-capable source (ListenBrainz, Last.fm, or directly linked Spotify). Apple Music, Amazon Music and YouTube Music exports never produce Live.
- BR-02 **Precedence.** Live beats Recent; the newest Recent across sources beats Top-Tracks; Top-Tracks merges all sources.
- BR-03 **Spotify isolation.** Data obtained through the Spotify Web API is shown only to the linked user and their friends with Spotify attribution and a link back to Spotify. It is never used for model training, never exported to another service, and is deleted within 24 hours of the user unlinking.
- BR-04 **Training data.** Recommendation and suggestion models train only on Jingle-native interactions (sends, plays of sends, votes, accepts), ListenBrainz data, and MusicBrainz metadata. Last.fm data is used for training only after a commercial agreement.
- BR-05 **Freshness labels.** Every feed card states its state and platform, for example "Live on Spotify" or "2 h ago on Apple Music"; the ingestion route is never shown (BR-14).

## 5. External interface requirements

Jingle exposes one versioned REST API and one WebSocket channel to its clients, and consumes nine external services through isolated adapters.

### 5.1 User interfaces

| Screen | Purpose | Key states |
| --- | --- | --- |
| Landing | Explain Jingle; start sign-up | Dark default, light toggle |
| Onboarding | Sign up, choose sources, set privacy, find friends | Per-source success and failure |
| Home feed | Friends' Live, Recent, Top-Tracks cards; shelves | Empty, loading, degraded (cached) |
| Friends | Requests, suggestions with reasons, search | No suggestions yet |
| Circles | Circle list, circle page, battle, circle feed | Invite pending, full circle |
| Profile | Compatibility, taste evolution, history | Limited shared data |
| Blend and Session | Blend tracks with reasons; live queue with votes | Reconnecting |
| Rituals | Weekly battle; monthly recap | Voting closed, no nominations |
| Settings | Sources, privacy, notifications, data export and deletion | Source needs re-consent |

UI rules: every screen has default, loading, empty and error states; dark and light themes; a persistent bottom player-style bar showing the user's own now-playing; keyboard operable; 44 × 44 px minimum touch targets.

### 5.2 Hardware interfaces

None beyond a device that runs a supported browser, or iOS 17+ and Android 12+ for the mobile apps.

### 5.3 Software interfaces

| Interface | Protocol | Used for | Limit to respect |
| --- | --- | --- | --- |
| ListenBrainz API | REST, token | Playing-now, listens, stats | Rate-limit headers |
| Last.fm API | REST, API key | Now-playing, recent tracks, tags | Enforced limits; non-commercial terms |
| Apple Music API | REST, developer JWT + user token | Recent played, heavy rotation, catalog, playlists | Token expiry; Apple terms |
| Spotify Web API | REST, OAuth 2.0 PKCE | Allowlisted testers only; later Extended Quota | Rolling 30-second limit, HTTP 429 with Retry-After |
| Amazon Music Web API | REST, Login with Amazon | Flagged; library and playlists | Closed beta |
| Google Data Portability API | REST, OAuth restricted scope | YouTube activity export every 24 h | Google app approval |
| MusicBrainz + Cover Art Archive | REST | Recording identity, tags, artwork | 1 request/second per client IP |
| Ticketmaster Discovery API | REST, API key | Concert events | [5,000 calls/day, 5 requests/second](https://developer.ticketmaster.com/products-and-docs/apis/getting-started/) |
| Firebase Cloud Messaging | HTTPS | Web and mobile push | Per-project quotas |

### 5.4 Communications interfaces

- HTTPS with TLS 1.2+ for all traffic; HSTS enabled.
- REST API at `/api/v1/`, JSON, OpenAPI 3.1 schema published.
- WebSocket (Socket.IO over WSS) at `/rt` for sessions, votes, presence and feed pushes.
- Email through a transactional provider with SPF, DKIM and DMARC.

### 5.5 Data contracts

**FeedCard** (server → client)

| Field | Type | Rule |
| --- | --- | --- |
| `friend_id` | UUID | Always |
| `state` | `LIVE` \| `RECENT` \| `TOP` \| `HIDDEN` | Always; BR-01 governs LIVE |
| `source` | `SPOTIFY` \| `APPLE_MUSIC` \| `AMAZON_MUSIC` \| `YOUTUBE_MUSIC` \| `UNKNOWN` | Platform the user played on |
| `via` | `DIRECT` \| `LISTENBRAINZ` \| `LASTFM` \| `EXPORT` | How Jingle learned it |
| `recording` | object: id, title, artist, artwork\_url, links per platform | Omitted when HIDDEN |
| `observed_at` | ISO-8601 UTC | Omitted when the friend hides precise time |
| `freshness_label` | string | Built server-side, e.g. "Live on Apple Music via ListenBrainz" |

**CompatibilityScore**: `score` 0–100; `shared_artists[]`; `shared_genres[]`; `audio_features_available` boolean; `audio_delta` object only when true; `reasons[]` of at most 3 strings. The score is never sent without its breakdown.

**Suggestion**: `user_id`, `score` 0–1, `reasons[]` (for example "4 mutual friends", "both love Kendrick Lamar"), `source_signals[]`.

**Error envelope**: `{"error": {"code": "SOURCE_REAUTH_REQUIRED", "message": "...", "details": {}, "request_id": "..."}}` with the matching HTTP status.

## 6. Functional requirements (product backlog)

The release backlog holds 13 epics and 106 stories; each epic below lists its stories with MoSCoW priority, and the key stories carry Gherkin acceptance criteria that become automated tests.

### EP-01 Accounts, onboarding and source linking

| ID | Story | Priority |
| --- | --- | --- |
| JNG-01-01 | As a visitor, I want to sign up with email, Google or Apple, so that I can start in under a minute | Must |
| JNG-01-02 | As a member, I want to connect ListenBrainz or Last.fm, so that friends see what I play on any platform | Must |
| JNG-01-03 | As a member, I want to connect Apple Music, so that my recent plays and heavy rotation appear | Must |
| JNG-01-04 | As an allowlisted tester, I want to connect Spotify directly, so that the team can validate the Spotify adapter | Should |
| JNG-01-05 | As a Spotify listener without direct access, I want a guided way to route Spotify through ListenBrainz or Last.fm, so that I still appear Live | Must |
| JNG-01-06 | As a member, I want to import my YouTube Music Takeout file, so that my YouTube taste counts | Must |
| JNG-01-07 | As a member, I want to authorise automatic YouTube exports through the Data Portability API, so that I need not re-upload | Could |
| JNG-01-08 | As a member, I want to connect Amazon Music once it is available, so that my library contributes | Could |
| JNG-01-09 | As a member, I want to unlink any one source without losing the others | Must |
| JNG-01-10 | As a member, I want to delete my account and all my data from inside the app | Must |
| JNG-01-11 | As a member, I want to be told when a source needs re-consent, so that my profile stays current | Must |
| JNG-01-12 | As a new member, I want a 4-step onboarding (profile, sources, privacy, friends), so that I reach a useful feed fast | Must |

**JNG-01-13 (Must):** As a member on any platform, I want to point my scrobbler app at Jingle's push endpoint, so that I show as Live within seconds.

```gherkin
Feature: Connect a scrobbling bridge (JNG-01-02)
  Scenario: Valid ListenBrainz token
    Given I am signed in and on the Sources screen
    When I paste a valid ListenBrainz user token and press Connect
    Then the source shows "Connected" within 3 seconds
    And my last 50 listens are imported within 60 seconds

  Scenario: Invalid token
    Given I am on the Sources screen
    When I paste a token that ListenBrainz rejects
    Then I see "That token didn't work — copy it again from ListenBrainz settings"
    And no source record is created

Feature: Spotify tester allowlist (JNG-01-04)
  Scenario: Non-allowlisted user
    Given the Spotify Development Mode allowlist is full at 5 users
    When a member who is not on it opens Connect Spotify
    Then they see the bridge guide from JNG-01-05 instead of an OAuth button
```

### EP-02 Social graph and privacy

| ID | Story | Priority |
| --- | --- | --- |
| JNG-02-01 | As a member, I want to find people by username, display name or invite link | Must |
| JNG-02-02 | As a member, I want to send, accept, decline and cancel friend requests | Must |
| JNG-02-03 | As a member, I want to remove a friend, so that they stop seeing my activity at once | Must |
| JNG-02-04 | As a member, I want to block and report a user | Must |
| JNG-02-05 | As a member, I want to hide my precise last-active time | Must |
| JNG-02-06 | As a member, I want a Private mode that hides all my activity for a chosen time (1 h, 8 h, until off) | Should |
| JNG-02-07 | As a member, I want to share a QR code or invite link that auto-sends a request | Should |
| JNG-02-08 | As a member, I want to add a bridged friend from an imported list, marked "No account" | Could |

```gherkin
Feature: Remove and block (JNG-02-03, JNG-02-04)
  Scenario: Blocking hides everything both ways
    Given Asha and Ravi are friends
    When Asha blocks Ravi
    Then within 5 seconds neither sees the other in feed, search, suggestions, circles or sessions
    And Ravi receives no notification of the block

  Scenario: Duplicate request
    Given Ravi has a pending request to Asha
    When Asha sends a request to Ravi
    Then both requests resolve into one accepted friendship
```

### EP-03 Friend suggestions

| ID | Story | Priority |
| --- | --- | --- |
| JNG-03-01 | As a member, I want up to 20 ranked suggestions, each with at most 3 reasons | Must |
| JNG-03-02 | As a member, I want suggestions from mutual friends (friends of friends) | Must |
| JNG-03-03 | As a member, I want "taste twin" suggestions of people with similar listening, even with no mutuals | Must |
| JNG-03-04 | As a member, I want to opt in to contact matching, with contacts hashed on my device | Should |
| JNG-03-05 | As a member, I want to dismiss a suggestion so it does not return for 90 days | Must |
| JNG-03-06 | As a member, I want to turn off my own discoverability | Must |
| JNG-03-07 | As a new member with no signals, I want a starter state (invite link, popular circles near my college, taste twins) | Must |
| JNG-03-08 | As a member, I want suggestions from people I shared a session, battle or concert with | Should |

```gherkin
Feature: Suggestion safety (JNG-03-01, JNG-03-06)
  Scenario: Excluded people never appear
    Given Meera has blocked Arjun, or Arjun turned discoverability off, or Meera dismissed Arjun 30 days ago
    When Meera's suggestions are generated
    Then Arjun is not in the list

  Scenario: Reasons never leak private listening
    Given Arjun has Private mode on
    When Arjun appears as a suggestion for Meera
    Then the reasons use only public profile data and mutual-friend counts
    And no track, artist or listening time from Arjun is shown

  Scenario: Minors and adults
    Given Meera is 16 and Arjun is 24
    When suggestions are generated for either
    Then neither appears in the other's suggestions
```

### EP-04 Friend circles

| ID | Story | Priority |
| --- | --- | --- |
| JNG-04-01 | As a member, I want to create a circle with a name, cover and up to 50 members | Must |
| JNG-04-02 | As a circle owner, I want to invite friends or share a link that expires in 7 days | Must |
| JNG-04-03 | As a circle owner, I want Owner, Admin and Member roles | Must |
| JNG-04-04 | As a circle member, I want a circle feed of members' activity | Must |
| JNG-04-05 | As a member, I want Jingle to suggest a circle from friends with shared taste, which I can accept or ignore | Should |
| JNG-04-06 | As a circle member, I want to leave a circle, and admins can remove members | Must |
| JNG-04-07 | As a circle admin, I want to set the battle schedule and whether members can invite | Should |
| JNG-04-08 | As a member, I want to be in up to 20 circles | Must |

```gherkin
Feature: Circle limits and suggestions (JNG-04-01, JNG-04-05)
  Scenario: Full circle
    Given a circle has 50 members
    When someone opens its invite link
    Then they see "This circle is full" and are not added

  Scenario: Suggested circle is never auto-joined
    Given the circle detector finds 5 friends with shared taste
    When it suggests "Indie night crew" to one of them
    Then no one is added until each person accepts an invite
```

### EP-05 Activity feed

| ID | Story | Priority |
| --- | --- | --- |
| JNG-05-01 | As a member, I want each friend's card to show Live, Recent or Top-Tracks with its source and freshness | Must |
| JNG-05-02 | As a member, I want Live cards to update without refreshing | Must |
| JNG-05-03 | As a member, I want to filter the feed by circle | Must |
| JNG-05-04 | As a member, I want to open any track in my own music app | Must |
| JNG-05-05 | As a member, I want to react to a friend's track with an emoji | Should |
| JNG-05-06 | As a member, I want a "Live now" shelf of friends playing right now | Must |
| JNG-05-07 | As a member, I want the feed to keep working from cache when a source is down, with honest timestamps | Must |
| JNG-05-08 | As a new member with no friends, I want an empty state that helps me add friends | Must |

```gherkin
Feature: No false Live (JNG-05-01, BR-01)
  Scenario: Apple Music only
    Given Kabir has only Apple Music linked
    When his card is rendered
    Then its state is RECENT or TOP and never LIVE

  Scenario: Stale now-playing
    Given Kabir's last ListenBrainz playing-now signal is 120 seconds old
    When his card is rendered
    Then its state is RECENT with label "2 min ago"
```

### EP-06 Recommendations and mixtapes

| ID | Story | Priority |
| --- | --- | --- |
| JNG-06-01 | As a member, I want to send a track to one or more friends with a note of up to 280 characters | Must |
| JNG-06-02 | As a member, I want to send a mixtape of 5–8 tracks | Must |
| JNG-06-03 | As a recipient, I want the track to open on my own platform | Must |
| JNG-06-04 | As a sender, I want to see Sent, Delivered, Viewed, Played | Must |
| JNG-06-05 | As a sender, I want a discovery credit when the artist I sent enters the friend's top artists | Should |
| JNG-06-06 | As a recipient, I want to reply with a reaction or a track | Should |
| JNG-06-07 | As a member, I want an inbox of received recommendations | Must |

```gherkin
Feature: Cross-platform send (JNG-06-03)
  Scenario: Spotify track to an Apple Music friend
    Given Riya sends a track resolved to a Recording with an ISRC
    When Dev, who uses Apple Music, opens it
    Then the Open button deep-links to the Apple Music version

  Scenario: No match on the friend's platform
    Given the Recording has no Apple Music link
    When Dev opens it
    Then he sees "Not found on Apple Music" and a search link
```

### EP-07 Blends and live sessions

| ID | Story | Priority |
| --- | --- | --- |
| JNG-07-01 | As a member, I want to generate a Blend with 2–6 friends or a whole circle | Must |
| JNG-07-02 | As a member, I want every Blend track to show a one-line reason | Must |
| JNG-07-03 | As a member, I want to regenerate a Blend and keep tracks I pinned | Should |
| JNG-07-04 | As a member, I want to save a Blend to my own platform as a playlist where its API allows | Should |
| JNG-07-05 | As a host, I want to start a live session and invite friends or a circle | Must |
| JNG-07-06 | As a participant, I want to add tracks to a shared queue, optionally anonymously | Must |
| JNG-07-07 | As a participant, I want one up or down vote per queued track, with the queue re-ordering live | Must |
| JNG-07-08 | As a participant, I want the session to survive the host leaving | Must |
| JNG-07-09 | As a participant, I want to rejoin after a dropped connection and see the current queue | Must |

```gherkin
Feature: Live queue (JNG-07-07, JNG-07-09)
  Scenario: Concurrent votes
    Given 30 participants are in a session
    When 10 of them vote on the same track within one second
    Then all 10 votes count
    And every participant sees the same order within 1 second at p95

  Scenario: Reconnect
    Given my connection drops for 20 seconds
    When it returns
    Then my queue matches the server's within 2 seconds
```

### EP-08 Taste compatibility and analytics

| ID | Story | Priority |
| --- | --- | --- |
| JNG-08-01 | As a member, I want a 0–100 compatibility score with any friend, with its breakdown | Must |
| JNG-08-02 | As a member, I want to see shared artists, shared genres and, where available, audio-feature overlap | Must |
| JNG-08-03 | As a member, I want a 12-month taste-evolution timeline | Should |
| JNG-08-04 | As a member, I want to overlay a friend's timeline on mine, with their consent | Could |
| JNG-08-05 | As a member, I want a circle's taste map showing where each member sits | Could |
| JNG-08-06 | As a new member, I want an empty state explaining that analytics build over 2–4 weeks | Must |
| JNG-08-07 | As a member, I want my own stats: minutes, top artists, genres, platforms used | Must |

```gherkin
Feature: Explained score (JNG-08-01, JNG-08-02)
  Scenario: Audio features unavailable
    Given neither friend has tracks with analysed preview audio
    When the score is shown
    Then the breakdown says "Sound comparison unavailable" and no audio numbers appear
```

### EP-09 Rituals

| ID | Story | Priority |
| --- | --- | --- |
| JNG-09-01 | As a circle member, I want a weekly song battle: nominate, vote, leaderboard | Must |
| JNG-09-02 | As a circle member, I want one nomination and 3 votes per week, not on my own track | Must |
| JNG-09-03 | As a circle member, I want the leaderboard published within 5 minutes of voting closing | Must |
| JNG-09-04 | As a circle member, I want a season table of wins over 8 weeks | Should |
| JNG-09-05 | As a member, I want a monthly recap card within 48 hours of month start | Must |
| JNG-09-06 | As a member, I want to share my recap as an image or link | Must |
| JNG-09-07 | As a member, I want a streak for days I sent or received a recommendation | Could |
| JNG-09-08 | As a circle admin, I want to skip a week without breaking the season | Should |
| JNG-09-09 | As a member, I want a weekly "what your circles played" digest | Should |

```gherkin
Feature: Battle integrity (JNG-09-02)
  Scenario: Late vote
    Given voting closed at 21:00 IST on Sunday
    When a vote arrives at 21:00:05
    Then it is rejected with "Voting has closed"
    And the leaderboard is unchanged
```

### EP-10 Concerts and events

| ID | Story | Priority |
| --- | --- | --- |
| JNG-10-01 | As a member, I want alerts for shows within my chosen radius by artists I share with friends | Should |
| JNG-10-02 | As a member, I want to mark "Going" and see which friends are going, if they allow it | Should |
| JNG-10-03 | As a member, I want attendance private by default | Must |
| JNG-10-04 | As a member, I want to set my city and radius (10–200 km) | Should |
| JNG-10-05 | As a member, I want to mute alerts for an artist | Could |

### EP-11 Notifications and messaging

| ID | Story | Priority |
| --- | --- | --- |
| JNG-11-01 | As a member, I want in-app notifications for requests, sends, battles and recaps | Must |
| JNG-11-02 | As a member, I want web and mobile push, off by default until I allow it | Must |
| JNG-11-03 | As a member, I want per-type notification controls | Must |
| JNG-11-04 | As a member, I want quiet hours (default 23:00–08:00 local) | Should |
| JNG-11-05 | As a member, I want a weekly email digest I can turn off | Could |
| JNG-11-06 | As a member, I want to comment on a shared track in a short thread | Should |
| JNG-11-07 | As a member, I want no more than 5 push notifications a day unless I raise the limit | Must |

### EP-12 Admin, moderation and trust

| ID | Story | Priority |
| --- | --- | --- |
| JNG-12-01 | As a member, I want to report a user, circle, note or comment | Must |
| JNG-12-02 | As a moderator, I want a queue of reports with context and one-click actions | Must |
| JNG-12-03 | As a moderator, I want to warn, mute, suspend or ban, with an audit log | Must |
| JNG-12-04 | As a platform admin, I want per-source rate-limit budgets and live usage | Must |
| JNG-12-05 | As a platform admin, I want feature flags per source and per feature | Must |
| JNG-12-06 | As a platform admin, I want to manage the Spotify tester allowlist | Should |
| JNG-12-07 | As the system, I want to filter profanity and slurs in names, notes and comments | Must |
| JNG-12-08 | As a member, I want to appeal a moderation action | Should |

### EP-13 Platform qualities

| ID | Story | Priority |
| --- | --- | --- |
| JNG-13-01 | As the team, we want the system to hold 5,000 concurrent users in a load test | Must |
| JNG-13-02 | As the team, we want dashboards and alerts for every NFR | Must |
| JNG-13-03 | As the team, we want daily backups with a tested restore | Must |
| JNG-13-04 | As a member, I want to download my data as JSON | Must |
| JNG-13-05 | As the team, we want zero-downtime deploys | Should |
| JNG-13-06 | As the team, we want contract tests for every source adapter | Must |
| JNG-13-07 | As a member, I want the app usable with a screen reader and keyboard | Must |
| JNG-13-08 | As the team, we want a status page | Should |

## 7. Non-functional requirements

Jingle shall serve 5,000 concurrent users at p95 API latency of 300 ms or less and 99.5% monthly availability, and every target below is checked by a named test or dashboard.

### 7.1 Performance

| ID | Requirement | Verified by |
| --- | --- | --- |
| NFR-PERF-01 | REST read endpoints: p95 ≤ 300 ms, p99 ≤ 800 ms at peak load | k6 load test; APM |
| NFR-PERF-02 | REST write endpoints: p95 ≤ 500 ms | k6; APM |
| NFR-PERF-03 | Home feed for up to 200 friends: server time p95 ≤ 500 ms | k6 scenario "feed" |
| NFR-PERF-04 | WebSocket fan-out of a vote or queue change: p95 ≤ 1 s to all session members | k6 WebSocket scenario |
| NFR-PERF-05 | A friend's Live change appears in viewers' feeds within 60 s at p95 | Synthetic probe |
| NFR-PERF-06 | Landing and home pages: Largest Contentful Paint ≤ 2.5 s on a 4G mobile profile | Lighthouse CI |
| NFR-PERF-07 | Takeout import of 50 MB completes in ≤ 30 s, asynchronously, with progress shown | Integration test |
| NFR-PERF-08 | Suggestions list returns in ≤ 200 ms from precomputed results | APM |

### 7.2 Scalability and capacity

| ID | Requirement |
| --- | --- |
| NFR-SCAL-01 | Hold 5,000 concurrent users (5,000 open WebSocket connections plus their REST traffic) for 30 minutes with error rate below 0.5% |
| NFR-SCAL-02 | Sustain 1,000 REST requests per second at the targets in 7.1 |
| NFR-SCAL-03 | Ingest 20,000 listening events per minute without backlog growth |
| NFR-SCAL-04 | Every stateless service scales horizontally; adding one replica shall raise capacity by at least 80% of one replica's measured throughput |
| NFR-SCAL-05 | Keep 2× headroom over measured peak on CPU, database connections and Redis memory |
| NFR-SCAL-06 | External API calls stay under 80% of each source's rate budget, enforced by per-source token buckets |

### 7.3 Availability and resilience

| ID | Requirement |
| --- | --- |
| NFR-AVAIL-01 | 99.5% monthly availability for sign-in, feed, send and sessions, excluding outages of external music platforms |
| NFR-AVAIL-02 | Recovery point objective 15 minutes; recovery time objective 1 hour |
| NFR-AVAIL-03 | An outage of any one source degrades only that source's cards to cached data with true timestamps |
| NFR-AVAIL-04 | Retries use exponential backoff with jitter, at most 3 attempts, and honour Retry-After |
| NFR-AVAIL-05 | Deploys cause no user-visible downtime (rolling updates, readiness probes) |

### 7.4 Security

| ID | Requirement |
| --- | --- |
| NFR-SEC-01 | All third-party tokens are encrypted at rest with AES-256-GCM under a KMS-managed key and never sent to clients |
| NFR-SEC-02 | The application meets OWASP ASVS 4.0 Level 2 controls for authentication, session and access control |
| NFR-SEC-03 | Session cookies are HttpOnly, Secure, SameSite=Lax; access tokens live 15 minutes |
| NFR-SEC-04 | Per-user and per-IP rate limits on auth, search, friend requests (30/day) and reports |
| NFR-SEC-05 | Every WebSocket event that changes state re-checks the sender's membership |
| NFR-SEC-06 | Dependency and container scans block any critical vulnerability in CI |
| NFR-SEC-07 | Uploaded files are scanned and parsed in an isolated worker, and deleted within 24 hours of parsing |

### 7.5 Privacy and compliance

| ID | Requirement |
| --- | --- |
| NFR-PRIV-01 | A plain-language DPDP consent notice lists each purpose; consent is itemised and withdrawable as easily as given |
| NFR-PRIV-02 | Until the verifiable parental-consent flow (DPDP Rule 10) ships, sign-up is limited to users aged 18 or over; once it ships, minor accounts get no adult suggestions, no public circles and no location |
| NFR-PRIV-03 | Account deletion removes personal data within 30 days and Spotify-sourced data within 24 hours of unlinking |
| NFR-PRIV-04 | A personal-data breach is reported to the Data Protection Board and affected users without delay, with a detailed report within 72 hours |
| NFR-PRIV-05 | Contact matching hashes identifiers on the device with a server-issued salt; raw contacts are never uploaded or stored |
| NFR-PRIV-06 | Users can export all their data as JSON within 48 hours of request |
| NFR-PRIV-07 | Platform branding rules are followed: Spotify content attributed and linked back; Last.fm "powered by AudioScrobbler" credit; ListenBrainz credit |

### 7.6 Accessibility and usability

| ID | Requirement |
| --- | --- |
| NFR-A11Y-01 | Zero WCAG 2.2 AA failures in automated scans; manual screen-reader pass per release |
| NFR-A11Y-02 | Text contrast at least 4.5:1 in both themes; focus visible on every control |
| NFR-A11Y-03 | All motion respects prefers-reduced-motion |
| NFR-A11Y-04 | A new user reaches a populated feed in 5 minutes or less in usability testing, for 8 of 10 participants |

### 7.7 Observability and maintainability

| ID | Requirement |
| --- | --- |
| NFR-OBS-01 | Every request carries a trace ID across Next.js, Django, FastAPI, Node and Celery (OpenTelemetry) |
| NFR-OBS-02 | Dashboards show every 7.1–7.3 target with alerts at 80% of its budget |
| NFR-OBS-03 | A false-Live count above 0 in any 5-minute window pages the on-call person |
| NFR-OBS-04 | Logs are structured JSON with `source` and `request_id`; no tokens or emails in logs |
| NFR-OBS-05 | Backend code keeps at least 80% unit coverage; every adapter has contract tests against recorded fixtures |

## 8. Business rules, retention, traceability and glossary

Twelve business rules bind every epic, and each epic traces to a user need, its NFRs and its test suite.

### 8.1 Business rules

| ID | Rule |
| --- | --- |
| BR-01 | No false Live (Section 4.5) |
| BR-02 | Source precedence: Live > newest Recent > merged Top (Section 4.5) |
| BR-03 | Spotify API data is isolated and display-only (Section 4.5) |
| BR-04 | Models train only on permitted data (Section 4.5) |
| BR-05 | Every card states its source and freshness (Section 4.5) |
| BR-06 | Activity is visible only between accepted friends, or within a circle the user joined |
| BR-07 | A block overrides every other relationship, circle and session |
| BR-08 | No one is added to a circle or session without accepting |
| BR-09 | A compatibility score is never shown without its breakdown |
| BR-10 | Concert attendance is private unless the user turns it on |
| BR-11 | Amazon Music linking stays hidden while its feature flag is off |
| BR-12 | Import-only and bridged profiles never receive playback or queue commands |

### 8.2 Data retention

| Data | Kept for | Then |
| --- | --- | --- |
| Raw listening events | 13 months | Rolled up into monthly taste snapshots, then deleted |
| Taste snapshots and recaps | Life of the account | Deleted with the account |
| Spotify API responses | Only while linked | Deleted within 24 h of unlinking |
| Takeout upload files | Until parsed | Deleted within 24 h |
| Moderation records | 2 years | Anonymised |
| Application logs | 30 days | Deleted |
| Backups | 35 days | Rotated |

### 8.3 Traceability

| Epic | User need (PRD) | Key NFRs | Test suite |
| --- | --- | --- | --- |
| EP-01 | "Use Jingle whatever app I use" | PERF-07, SEC-01, PRIV-01, PRIV-03 | `tests/sources`, adapter contracts |
| EP-02 | "Control who sees me" | SEC-04, PRIV-02 | `tests/social` |
| EP-03 | "Find my people" | PERF-08, PRIV-05 | `tests/suggestions`, offline eval |
| EP-04 | "Hang out with my crew" | SEC-05 | `tests/circles` |
| EP-05 | "See what friends play now" | PERF-03, PERF-05, AVAIL-03, OBS-03 | `tests/feed`, synthetic probe |
| EP-06 | "Share music that lands" | PERF-02 | `tests/recs` |
| EP-07 | "Listen together" | PERF-04, SCAL-01 | `tests/sessions`, k6 WebSocket |
| EP-08 | "Know why we match" | PERF-01 | `tests/analytics` |
| EP-09 | "A reason to come back" | AVAIL-01 | `tests/rituals` |
| EP-10 | "Go to shows together" | PRIV-01 | `tests/concerts` |
| EP-11 | "Hear about it, not too much" | — | `tests/notify` |
| EP-12 | "Feel safe" | SEC-02 | `tests/moderation` |
| EP-13 | "It just works" | All SCAL, AVAIL, OBS | k6 suite, chaos drills |

### 8.4 Glossary

| Term | Meaning |
| --- | --- |
| Blend | A shared playlist built from 2–6 members' tastes, each track with a reason |
| Bridge | ListenBrainz or Last.fm: services users scrobble to, which Jingle reads |
| Circle | A named group of up to 50 members that scopes a feed, Blends and a weekly battle |
| Live | A now-playing signal under 90 seconds old from a live-capable source |
| Recording | Jingle's canonical track, matched across platforms by ISRC, MBID or fuzzy match |
| Scrobble | A record of a play sent by a player or app to a bridge |
| Taste twin | A suggested person with high taste similarity and no mutual friends |

### 8.5 Open issues

- [ ] Seek a Last.fm commercial agreement before any revenue or before using Last.fm data in models.
- [ ] Ask Spotify, in writing, whether a display-only Spotify panel inside a multi-platform app is acceptable under Policy III.5; until answered, direct Spotify stays limited to the 5-tester allowlist.
- [ ] Apply for Google verification of the restricted `dataportability.myactivity.youtube` scope.
- [ ] Request Amazon Music Web API access through Amazon business development.
- [ ] Confirm the exact Apple Music recently-played item limit during the Apple adapter spike.
- [ ] Confirm launch age policy (18+ at launch) with the faculty guide.

### Sources

- [Spotify: February 2026 Development Mode migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide)
- [TechCrunch: Spotify changes developer mode API (6 Feb 2026)](https://techcrunch.com/2026/02/06/spotify-changes-developer-mode-api-to-require-premium-accounts-limits-test-users/)
- [Spotify Developer Policy](https://developer.spotify.com/policy)
- [Amazon Music Web API V2 overview](https://developer.amazon.com/docs/music/API_web_overview_v2.html)
- [Google Data Portability API: introduction](https://developers.google.com/data-portability/user-guide/introduction) and [scopes](https://developers.google.com/data-portability/user-guide/scopes)
- [Last.fm API terms](https://www.last.fm/api/tos) and [user.getRecentTracks](https://www.last.fm/api/show/user.getRecentTracks)
- [ListenBrainz core API](https://listenbrainz.readthedocs.io/en/latest/users/api/core.html)
- [Ticketmaster Discovery API: getting started](https://developer.ticketmaster.com/products-and-docs/apis/getting-started/)
- [DPDP Act and Rules timeline](https://www.sansalegal.com/post/dpdp-act-2023-and-rules-2025-phased-implementation-timeline-and-business-compliance-deadlines); [DPDP Rule 10](https://www.dpdpa.com/dpdparules/rule10.html)
