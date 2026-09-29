# Jingle — Technical Bible

Sep 29, 2026 · @Shlok

## 1. System architecture and service boundaries

Jingle is four services (core-api, ingest-ml, realtime, workers) around a shared data layer, and the most important path in the system is the one that turns a friend's play into a Live card within 60 seconds.

&#91;embedded content: listen ingestion path · 8 steps\]

The bridges give Live for any platform whose player scrobbles; directly linked Apple Music and YouTube exports add history but never Live, as SRS BR-01 requires.

### 1.1 Boundaries

| Rule | Why |
| --- | --- |
| Only ingest-ml imports platform SDKs or calls platform APIs | One place to enforce rate limits, terms and contract tests |
| Only core-api writes business tables in PostgreSQL | One owner for invariants such as blocks, circle limits and battle rules |
| realtime never writes to PostgreSQL | Sockets stay fast; state changes go through core-api or Redis |
| workers run code from core-api and ingest-ml packages, not their own copies | No drift between synchronous and background paths |
| Services talk through HTTP with service tokens, or through Redis Streams events | Clear contracts, easy tracing |

### 1.2 Repository layout (monorepo)

```text
jingle/
  apps/
    web/            Next.js client and /design route
    realtime/       Node + Express + Socket.IO
  services/
    core_api/       Django project: accounts, social, circles, recs, rituals, moderation
    ingest_ml/      FastAPI: adapters/, identity/, inference/
  packages/
    py-common/      shared Pydantic models, event schemas, OTel setup
    ts-client/      OpenAPI-generated TypeScript client
    design-tokens/  colours, type, spacing for web and mobile
  infra/
    helm/  terraform/  k6/  docker-compose.yml
  docs/
    adr/            architecture decision records
```

### 1.3 Environments

| Environment | Purpose | Data |
| --- | --- | --- |
| Local | Docker Compose, all services | Seeded fake users and recorded platform fixtures |
| Preview | One per pull request (web only) | Staging API |
| Staging | k3s cluster mirroring production | Synthetic users plus the 5 Spotify testers |
| Production | Managed Kubernetes, India region | Real users |

Architecture decisions are recorded as ADRs in `docs/adr/`; the first five are: bridge-first ingestion, MongoDB for listens, Node for realtime, Qdrant for vectors, and display-only Spotify.

## 2. Source adapter layer

Every platform implements one Python interface in ingest-ml, declares its capabilities, and raises `NotSupported` for anything it cannot do, which makes a false Live state a code error that tests catch.

### 2.1 The interface

```python
class Capabilities(BaseModel):
    live: bool
    recent: bool
    top: bool
    playlist_write: bool
    trainable: bool          # may this data feed models? (SRS BR-04)

class SourceAdapter(Protocol):
    kind: SourceKind         # LISTENBRAINZ | LASTFM | APPLE_MUSIC | SPOTIFY | AMAZON_MUSIC | YOUTUBE_EXPORT
    caps: Capabilities

    async def link(self, user_id: UUID, credential: LinkCredential) -> LinkedSource: ...
    async def refresh(self, src: LinkedSource) -> LinkedSource: ...
    async def now_playing(self, src: LinkedSource) -> NowPlaying | None: ...   # raises NotSupported if not caps.live
    async def recent(self, src: LinkedSource, since: datetime) -> list[RawListen]: ...
    async def top(self, src: LinkedSource, window: Window) -> list[RawTrack]: ...
    async def write_playlist(self, src: LinkedSource, pl: PlaylistSpec) -> str: ...

def assert_live(adapter: SourceAdapter) -> None:
    if not adapter.caps.live:
        raise NotSupported(f"{adapter.kind} cannot report now-playing")
```

The feed resolver only accepts `NowPlaying` objects created by an adapter whose `caps.live` is true; the object carries its adapter kind and `observed_at`, and the resolver rejects any older than 90 seconds.

### 2.2 Per-source behaviour

| Source | Auth and storage | Polling | Normalisation | Errors |
| --- | --- | --- | --- | --- |
| ListenBrainz | User token, encrypted (AES-256-GCM, KMS key) | `Only when the user does not push to Jingle: playing-now every 30 s while their card is on a friend's screen; listens every 15 min` | MBIDs from `additional_info` when present | 401 → mark needs re-consent; 429 → honour reset headers |
| Last.fm | Username (public) or session key | `user.getRecentTracks every 60 s while viewed, inside a 4 requests/s total budget` (`nowplaying="true"` → Live) | Artist/track MBIDs; strip "(Remastered)" etc. | Error 29 (rate limit) → back off; private profile → needs-attention state |
| Apple Music | Developer JWT signed ES256 (rotated every 90 days); Music User Token encrypted | Recent played every 10 min when active; heavy rotation daily | ISRC from catalog attributes | 401/403 → token refresh via MusicKit on next visit |
| Spotify (testers) | OAuth PKCE; refresh token encrypted | currently-playing every 20 s when active; recently-played every 5 min | ISRC from `external_ids` | 429 → `Retry-After`; stored only while linked |
| Amazon Music | Login with Amazon | Library sync daily | ISRC if present | Flag off → adapter not loaded |
| YouTube export | Upload or Data Portability job | One-off, or every 24 h with time-based consent | Title/channel parsing, then fuzzy match | Malformed file → field-level error message |

### 2.3 Adaptive polling

Polling runs only where someone will see the result:

1. A user counts as **active** if their app is open, or a friend has their card on screen, in the last 2 minutes (tracked in Redis presence).
2. Users who push scrobbles to Jingle (section 7.1) are never polled for Live. Active users on a poll-only live source are polled at the intervals and budgets in section 7.2; inactive users every 15 min for recents only.
3. Each poll task reschedules itself with ±20% jitter to avoid thundering herds.
4. A per-source Redis token bucket caps calls at 80% of the source's budget; when empty, the poll is skipped and the card shows its cached state with its true timestamp.

### 2.4 Normalised event

```json
{
  "event_id": "uuid",
  "user_id": "uuid",
  "recording_id": "uuid | null",
  "raw": {"artist": "Arijit Singh", "title": "Kesariya", "album": "Brahmastra"},
  "platform": "SPOTIFY | APPLE_MUSIC | AMAZON_MUSIC | YOUTUBE_MUSIC | UNKNOWN",
  "via": "LISTENBRAINZ | LASTFM | DIRECT | EXPORT",
  "kind": "NOW_PLAYING | LISTEN",
  "played_at": "2026-09-29T10:15:02Z",
  "observed_at": "2026-09-29T10:15:20Z",
  "trainable": true
}
```

`platform` comes from the scrobble's player field when the bridge reports it (for example ListenBrainz `music_service`), otherwise `UNKNOWN`. `trainable` is false for direct-Spotify and Last.fm events.

### 2.5 Jingle Connect: one button, invisible routing

The user sees one "Connect Spotify" button (and one each for Apple Music, YouTube Music and Amazon Music); a Connection Orchestrator decides behind it which route to use, keeps it healthy, and switches routes without the user noticing.

**Components**

| Component | Job |
| --- | --- |
| Connection Orchestrator (ingest-ml) | Picks the best available route per user, platform and device; records it in `linked_sources.route` |
| Jingle Companion | Jingle's own listening capture, so no third-party scrobbler is needed: a permission inside the Jingle Android app (reads the phone's now-playing media session) and a Jingle browser extension for desktop (a fork of the MIT-licensed Web Scrobbler, sending only to Jingle) |
| Route health monitor | Watches each route's freshness; if a route goes quiet or fails, falls back to the next one and only asks the user when their action is truly needed |
| Capability resolver | Every feature asks for a capability (Live, history, write playlist, queue), never a route; missing capabilities get a built-in fallback |
| Unified listening graph | All routes write the same normalised event; the route is internal metadata, never shown on a card |

**Route choice for Spotify** (first available wins; the user sees only Spotify's own approval screen, or one Jingle permission)

| Priority | Route | Used when | What the user sees |
| --- | --- | --- | --- |
| 1 | Direct Spotify API | A direct slot is free (5 in Development Mode; everyone after Extended Quota) | Spotify's login and approval screen |
| 2 | Jingle Companion | Android app or desktop browser | Spotify's approval screen for history (if a slot is free) or a single "Allow Jingle to see what's playing" permission |
| 3 | Last.fm bridge | iPhone with no direct slot | One approval screen inside a Jingle-styled sheet; Jingle then opens Spotify's Last.fm link page pre-filled, a single confirm |

The other platforms follow the same pattern: Apple Music uses MusicKit for history plus the Companion for Live; YouTube Music and Amazon Music use the Companion for Live and history, plus exports or the direct API when approved.

**Fallbacks from the capability resolver**

| Missing capability | What the user gets instead |
| --- | --- |
| Write playlist (no direct slot) | "Add to Spotify" opens each Blend track in Spotify in turn, or a shareable Jingle playlist page with one-tap track links |
| Queue control | "Play next" opens the track in the user's app |
| Live (e.g. companion not running) | Card shows Recent with the true time; no error, no setup prompt on the card |

**What cannot be hidden, and why.** Every platform requires the user to approve access themselves on that platform's own screen; no app is allowed to skip that consent. On iPhone, iOS blocks one app from reading another's playback, so the Last.fm route needs one extra confirm. Jingle keeps each of these to a single screen, styled as part of Jingle's own flow, and never mentions routes after setup. Required credits (Last.fm's "powered by AudioScrobbler") appear on the Settings → Connections page, not on feed cards.

## 3. Data model

Thirty-four PostgreSQL tables (including `taste_snapshots` and `consents`, sections 3.5 and 9.2) hold the system of record, three MongoDB collections hold listening and notification data, and Redis holds short-lived state; every table has a UUID primary key and `created_at`/`updated_at`.

### 3.1 PostgreSQL tables

| Domain | Table | Key columns | Notes |
| --- | --- | --- | --- |
| Accounts | `users` | id, username (unique, citext), display\_name, email, birth\_year, college, city, discoverable, private\_until | Soft delete with `deleted_at`; purge job at 30 days |
|  | `privacy_settings` | user\_id, activity\_visibility, show\_last\_active, concerts\_visible | 1:1 with users |
|  | `linked_sources` | id, user\_id, kind, external\_user\_id, token\_ciphertext, token\_key\_id, status, last\_ok\_at | Unique (user\_id, kind) |
| Social | `friendships` | user\_low\_id, user\_high\_id, status, requested\_by, accepted\_at | One row per pair, ordered ids avoid duplicates |
|  | `blocks` | blocker\_id, blocked\_id | Checked on every social query |
|  | `suggestion_feedback` | user\_id, candidate\_id, action (shown/accepted/dismissed), at | Training labels and 90-day dismiss rule |
| Circles | `circles` | id, name, owner\_id, visibility, member\_count, battle\_schedule | member\_count ≤ 50 by check constraint |
|  | `circle_members` | circle\_id, user\_id, role, joined\_at | Unique pair; role enum owner/admin/member |
|  | `circle_invites` | id, circle\_id, token\_hash, expires\_at, max\_uses | 7-day expiry |
| Music | `recordings` | id, isrc, mbid, title, artist\_name, duration\_ms, artwork\_url | Unique partial indexes on isrc and mbid |
|  | `recording_links` | recording\_id, platform, external\_id, url | Deep links per platform |
|  | `artists`, `artist_tags` | mbid, name; tag, weight | From MusicBrainz and Last.fm |
| Sharing | `recommendations` | id, sender\_id, note, kind (track/mixtape) |  |
|  | `recommendation_items` | rec\_id, recording\_id, position | 1 or 5–8 per rec |
|  | `recommendation_deliveries` | rec\_id, recipient\_id, delivered\_at, viewed\_at, played\_at | Status per recipient |
| Blends and sessions | `blends`, `blend_tracks` | blend\_id, recording\_id, reason, contributor\_ids | Reason text is required (SRS BR-09 spirit) |
|  | `sessions`, `session_queue`, `session_votes` | queue entry, added\_by (nullable when anonymous), vote value ±1 | Vote unique (entry, user) |
| Rituals | `battles`, `battle_nominations`, `battle_votes` | circle\_id, week\_start, phase; nominator; voter | Unique (battle, nominator), ≤ 3 votes per voter by trigger |
|  | `recaps` | user\_id, month, stats\_json, image\_url |  |
| Other | `concert_events`, `concert_attendance`, `notifications_prefs`, `reports`, `moderation_actions`, `feature_flags`, `audit_log` |  |  |

### 3.2 Key indexes

```sql
CREATE UNIQUE INDEX friendships_pair ON friendships (user_low_id, user_high_id);
CREATE INDEX friendships_accepted_low  ON friendships (user_low_id)  WHERE status = 'accepted';
CREATE INDEX friendships_accepted_high ON friendships (user_high_id) WHERE status = 'accepted';
CREATE UNIQUE INDEX recordings_isrc ON recordings (isrc) WHERE isrc IS NOT NULL;
CREATE UNIQUE INDEX recordings_mbid ON recordings (mbid) WHERE mbid IS NOT NULL;
CREATE INDEX deliveries_recipient ON recommendation_deliveries (recipient_id, delivered_at DESC);
CREATE UNIQUE INDEX session_vote_once ON session_votes (queue_entry_id, user_id);
```

A database view `v_friend_edges` unions both directions of accepted friendships for graph queries.

### 3.3 MongoDB collections

| Collection | Type | Fields | Retention |
| --- | --- | --- | --- |
| `listens` | Time-series (timeField `played_at`, metaField `{user_id, platform, via}`, granularity minutes) | recording\_id, raw, trainable | TTL 13 months |
| `provider_payloads` | Standard | source, request, response (redacted), fetched\_at | TTL 7 days (debugging only; never Spotify beyond link lifetime) |
| `notifications` | Standard | user\_id, type, payload, read\_at | TTL 90 days |

### 3.4 Redis keys

| Key | Type | TTL | Purpose |
| --- | --- | --- | --- |
| `np:{user_id}` | Hash | 90 s | Now-playing state for Live cards |
| `feed:{user_id}` | Sorted set | 10 min | Pre-ranked friend card order |
| `presence:{user_id}` | String | 120 s | Active flag for adaptive polling |
| `rl:{source}:{window}` | Token bucket | Window | Per-source rate budget |
| `sug:{user_id}` | List | 24 h | Precomputed suggestions |
| `sess:{id}:queue` | Sorted set | Session life | Live queue by score |

### 3.5 Monthly rollups

A monthly Celery job reads the month's `listens` into pandas, writes `taste_snapshots` (top artists, genre shares, minutes, platform mix) to PostgreSQL, and feeds the recap generator. After 13 months, raw listens expire; snapshots remain.

## 4. API design

Clients use one versioned REST API (`/api/v1/`, OpenAPI 3.1 generated by drf-spectacular) and one Socket.IO namespace (`/rt`); both share JWT auth, the error envelope and request IDs.

### 4.1 Conventions

| Topic | Rule |
| --- | --- |
| Versioning | URL prefix `/api/v1/`; breaking changes go to `/v2/`; old version kept 6 months |
| Auth | Access JWT (15 min) in memory; refresh token in an HttpOnly cookie, rotated on use |
| Pagination | Cursor-based: `?cursor=...&limit=20` (max 100); response has `next_cursor` |
| Idempotency | `Idempotency-Key` header required on POSTs that create sends, votes, nominations |
| Rate limits | 429 with `Retry-After`; headers `X-RateLimit-Limit` and `X-RateLimit-Remaining` |
| Errors | `{"error": {"code", "message", "details", "request_id"}}` with codes such as `SOURCE_REAUTH_REQUIRED`, `CIRCLE_FULL`, `VOTING_CLOSED`, `BLOCKED` |
| Time | ISO-8601 UTC in payloads; clients render local time (default Asia/Kolkata) |
| Caching | `ETag` on profile and circle reads; `Cache-Control: private` everywhere user-specific |

### 4.2 Key endpoints

| Method and path | Purpose | Story |
| --- | --- | --- |
| `POST /auth/register`, `/auth/login`, `/auth/refresh` | Sign up and sessions | JNG-01-01 |
| `GET /me`, `PATCH /me/privacy` | Profile and privacy | JNG-02-05 |
| `POST /sources/{kind}/link`, `DELETE /sources/{id}` | Link and unlink a source | JNG-01-02 to 09 |
| `POST /imports/youtube` (multipart) → `202` + job id | Takeout upload | JNG-01-06 |
| `GET /feed?circle={id}&cursor=` | Feed cards | JNG-05-01 |
| `GET /friends`, `POST /friends/requests`, `POST /friends/requests/{id}/accept` | Social graph | JNG-02-02 |
| `POST /blocks`, `POST /reports` | Safety | JNG-02-04, JNG-12-01 |
| `GET /suggestions`, `POST /suggestions/{user_id}/dismiss` | Friend suggestions | JNG-03-01, 05 |
| `POST /circles`, `POST /circles/{id}/invites`, `POST /circles/join/{token}` | Circles | JNG-04-01, 02 |
| `GET /circles/suggested` | Suggested circles | JNG-04-05 |
| `POST /recommendations`, `GET /inbox` | Sends and inbox | JNG-06-01, 07 |
| `POST /blends`, `POST /blends/{id}/regenerate` | Blends | JNG-07-01, 03 |
| `POST /sessions`, `POST /sessions/{id}/queue`, `POST /queue/{entry}/vote` | Live sessions (REST fallback) | JNG-07-05 to 07 |
| `GET /users/{id}/compatibility` | Explained score | JNG-08-01 |
| `GET /circles/{id}/battle`, `POST /battles/{id}/nominations`, `POST /battles/{id}/votes` | Battles | JNG-09-01, 02 |
| `GET /recaps/{yyyy-mm}` | Monthly recap | JNG-09-05 |
| `GET /me/export`, `DELETE /me` | Data rights | JNG-13-04, JNG-01-10 |

### 4.3 WebSocket events (`/rt`)

| Direction | Event | Payload | Notes |
| --- | --- | --- | --- |
| Client → server | `session:join` | `{session_id}` | Server checks membership and blocks |
| Client → server | `queue:add` | `{session_id, recording_id, anonymous}` | Idempotency key required |
| Client → server | `vote:cast` | `{entry_id, value: 1 \| -1}` | One per user per entry |
| Server → client | `queue:state` | Full ordered queue + `version` | Sent on join and reconnect |
| Server → client | `queue:delta` | Changed entries + new `version` | Client asks for `queue:state` if it sees a version gap |
| Server → client | `feed:update` | FeedCard | To friends and circle rooms |
| Server → client | `presence` | `{user_id, online}` | Throttled to 1 per 10 s per user |
| Server → client | `notify` | `{type, id}` | Client fetches details over REST |

Ordering: every queue change carries a monotonically increasing `version` from Redis `INCR`, so clients apply deltas in order and detect gaps after a reconnect.

## 5. Friend suggestions and friend circles

Suggestions come from a five-stage pipeline (generate, filter, score, diversify, explain) that runs nightly and on every new friendship; circles combine user-created groups with Leiden community detection that only ever *suggests* a circle.

### 5.1 Suggestion pipeline

1. **Generate candidates** (up to 800 per user): friends of friends (2 hops, up to 500); taste neighbours from Qdrant ANN (top 200, filtered to discoverable users in the same age band); co-members of circles, sessions, battles and concerts; opt-in contact matches; same college or city.
2. **Filter** (hard rules): remove existing friends, pending requests, blocked in either direction, discoverability off, dismissed in the last 90 days, suspended accounts, and any adult–minor pair.
3. **Score** each remaining candidate (formula below).
4. **Diversify** the top 20: at most 8 taste twins with zero mutual friends; maximal-marginal-relevance re-ranking so the list is not 20 people from one circle.
5. **Explain**: attach up to 3 reason templates from the strongest signals; reasons use only data the candidate shares with the viewer.

### 5.2 Scoring

Mutual-friend strength uses Adamic–Adar, which gives more weight to mutual friends who have few friends:

```latex
AA(u,v) = \sum_{w \in N(u) \cap N(v)} \frac{1}{\log \lvert N(w) \rvert}
```

Each signal is scaled to 0–1, then combined:

```latex
s = 0.35\,(1 - e^{-AA/2}) + 0.30\,\max\!\left(0, \tfrac{\cos(t_u, t_v) - 0.2}{0.8}\right) + 0.15\,s_{ctx} + 0.10\,s_{contact} + 0.10\,s_{local}
```

| Signal | Definition |
| --- | --- |
| t\_u, t\_v | 128-dimension taste vectors: TF-IDF over top artists and tags, reduced with TruncatedSVD, refreshed nightly |
| s\_ctx | min(1, 0.5 × shared circles + 0.3 × shared sessions + 0.2 × shared concerts) |
| s\_contact | 1 if an opt-in contact match, else 0 |
| s\_local | 1 for same college, 0.5 for same city, else 0 (both opt-in profile fields) |

From Release 3, a LightGBM ranker trained on `suggestion_feedback` (accepted = 1, dismissed or ignored after 14 days = 0) replaces the fixed weights once 10,000 labelled outcomes exist; the heuristic stays as a fallback.

### 5.3 Cold start

- No friends, no listening yet: onboarding asks for 3–5 favourite artists or genres to form a provisional taste vector; show taste twins, the user's college circles, and the invite link and QR.
- First friend accepted: recompute that user's suggestions within 60 seconds (event-driven Celery task).
- First 7 days of listening: taste vector refreshed daily instead of weekly.

### 5.4 Contact matching (opt-in)

Phone numbers are normalised to E.164 and hashed on the device as SHA-256(salt + number), using a salt the server issues and rotates weekly; raw numbers never leave the phone. The server keeps the same salted hash for each registered user's verified number, returns only matches, and discards every non-matching hash immediately; no contact list is stored. Salted hashes of phone numbers can still be brute-forced because the number space is small, so matching is limited to 1 upload a day per user, needs explicit consent, and uploads are dropped after comparison (SRS NFR-PRIV-05).

### 5.5 Circles

**User-created circles** follow SRS EP-04: up to 50 members, roles, 7-day invite links, private by default.

**Suggested circles**, weekly:

1. Build a weighted graph over accepted friendships only, with edge weight 0.5 + cos(t\_u, t\_v).
2. Run Leiden (python-igraph + leidenalg, resolution 1.0).
3. Keep communities of 3–12 members with mean edge weight of at least 0.9 that do not already match an existing circle (Jaccard overlap under 0.6).
4. Name the suggestion from the community's top shared genre ("Your indie crew"), editable by the user.
5. Show it to the member with the most internal edges; they choose whom to invite. Nobody joins without accepting (SRS BR-08). A dismissed suggestion is not shown again for 30 days.

### 5.6 Evaluation

| Metric | Method | Target |
| --- | --- | --- |
| Recall@20 | Offline: hide 20% of friendships formed in the last 30 days, replay candidates | ≥ 0.30 |
| Acceptance rate | Online: accepted ÷ shown | ≥ 8% |
| Coverage | Users with at least 5 suggestions | ≥ 90% |
| Safety | Blocked or minor pairs ever shown | 0 |
| Circle suggestion uptake | Suggested circles that get at least 3 members | ≥ 25% |

### 5.7 Cost

For 60,000 users with 800 candidates each, the nightly job scores about 48 million pairs, which vectorised NumPy on one 8-vCPU worker completes in well under an hour; results are cached in Redis `sug:{user_id}` for 24 hours.

## 6. Recommendation, compatibility and explanation pipeline

Scores and track choices are computed by deterministic formulas and models over permitted data; explanations are built from the same facts, and the language model may only rephrase them, never add to them.

### 6.1 Compatibility score

For friends u and v, using the last 90 days:

| Component | Measure | Weight with sound data | Weight without |
| --- | --- | --- | --- |
| Artists | Weighted Jaccard over each user's top 50 artists, weighted by play share | 0.45 | 0.60 |
| Genres | Cosine similarity of genre-share vectors (MusicBrainz and Last.fm tags) | 0.30 | 0.40 |
| Sound | 1 − normalised distance between mean tempo, energy, valence and danceability (Essentia) | 0.25 | — |

```latex
raw = \sum_k w_k \cdot c_k \qquad score = \text{round}\left(100 \cdot F_{pairs}(raw)\right)
```

F\_pairs is the empirical percentile of `raw` among all friend pairs, recalibrated monthly, so 50 means "a typical friendship" and the number spreads across 0–100. Sound is used only when both users have at least 20 analysed recordings; otherwise `audio_features_available` is false and the card says so (SRS JNG-08-02).

### 6.2 Blends

1. **Pool:** each member's top 100 recordings from the last 90 days, plus 50 LightFM candidates for the group.
2. **Affinity:** for each track and member, affinity = play share if they played it, else the LightFM score.
3. **Group utility:** mean affinity minus 0.5 × standard deviation, so tracks one person loves and others would dislike rank lower.
4. **Constraints:** 30 tracks; no member supplies more than 40%; at most 2 tracks per artist; resolvable on every member's platform where possible.
5. **Reason:** the strongest fact for each track, for example "Aanya and Kabir both played this in September" or "Dev's top artist; Meera plays a lot of similar indie pop".

### 6.3 Recommendations for a person

LightFM (WARP loss) with user features (taste vector, college) and item features (artist, tags, era) handles cold start; implicit ALS on Jingle-native plays improves warm users. The "You might send this to..." hint on a track uses the friend's predicted affinity above 0.7.

### 6.4 Discovery credit

When a delivered recommendation's artist enters the recipient's monthly top 20 within 60 days and was absent from their previous 6 months of listening, the sender gets a discovery credit. The check runs in the monthly snapshot job.

### 6.5 Explanation text

| Step | Rule |
| --- | --- |
| Facts | A JSON list of verified facts: names, artists, genres, counts, dates |
| Template | A deterministic template sentence is always produced first |
| Rephrase (optional) | A small self-hosted instruct model rewrites the template in at most 18 words, temperature 0.2 |
| Validate | Output may contain only names, artists and numbers present in the facts; no banned words; length check |
| Fallback | Any validation failure shows the template sentence |
| Cache | One explanation per (Blend, track) or (suggestion, candidate), regenerated only when facts change |

### 6.6 Model lifecycle

Models retrain weekly in a Celery `ml` queue; MLflow records data window, metrics and version. A new model ships only if offline precision@10 does not drop by more than 2% relative; rollback is one flag flip.

## 7. Realtime, async jobs and the polling budget

Polling bridges cannot carry 5,000 concurrent users on their public rate limits, so Jingle's primary live path is **push**: a ListenBrainz-compatible scrobble endpoint that users' scrobbler apps send to directly, with polling kept for sources that cannot push.

### 7.1 Push ingestion (primary at scale)

Jingle exposes `POST /ingest/1/submit-listens` and `POST /ingest/1/playing-now`, following the open [ListenBrainz API](https://listenbrainz.readthedocs.io/en/latest/users/api/core.html) format, authenticated with a per-user Jingle scrobble token.

| Client | How it reaches Jingle | Covers |
| --- | --- | --- |
| Web Scrobbler (browser extension) | Custom ListenBrainz endpoint set to Jingle | YouTube Music, Spotify web, Apple Music web, Amazon Music web |
| Pano Scrobbler (Android) | Custom ListenBrainz instance set to Jingle | Any Android player that posts media notifications |
| Desktop scrobblers (Windows, macOS) | ListenBrainz-compatible target | Desktop apps |
| Jingle mobile app (R3, Android) | Reads media sessions with permission | All players on the device |

Jingle can **relay** each received scrobble on to the user's own ListenBrainz or Last.fm account, so users keep their history there. Support for custom endpoints in each scrobbler is confirmed in the Sprint 2 spike before the onboarding copy is final.

### 7.2 Polling (fallback)

| Source | Who needs polling | Interval | Budget rule |
| --- | --- | --- | --- |
| Last.fm | iPhone Spotify and Apple Music users whose only live path is Last.fm | 60 s, only while a friend has their card on screen | At most 4 requests/s in total until a Last.fm agreement raises it (Last.fm publishes no number; about 5/s per IP is the common guidance) |
| ListenBrainz (poll) | Users who scrobble to ListenBrainz but not to Jingle | 30 s when viewed | Obey `X-RateLimit-*` headers; at most 80% of the reported limit |
| Apple Music | Linked Apple Music users | 10 min when active | Per-user tokens; stay under 1 request/s per user |
| Spotify (testers) | 5 allowlisted testers | 20 s | Under Spotify's rolling 30 s limit |

**What the budget buys:** 4 Last.fm calls a second at a 60 s interval keeps 240 simultaneously-viewed Last.fm-only users Live. Everyone else is Live through push, or shows Recent honestly. The metric "Live coverage" (PRD 4.3) tracks how many friend cards are Live or Recent; if Last.fm-only users grow past the budget, the onboarding pushes harder toward push setup, and a Last.fm commercial agreement is pursued.

### 7.3 Realtime gateway

| Aspect | Design |
| --- | --- |
| Rooms | `user:{id}` (personal), `friends:{id}` (fan-out of one user's updates), `circle:{id}`, `session:{id}` |
| Fan-out | A `listen.observed` event publishes to `friends:{id}`; sockets of online friends are joined to that room at connect time |
| Scale | 5,000 sockets across 3 Node pods (about 1,700 each) with @socket.io/redis-adapter and sticky sessions; one pod can fail without dropping below capacity |
| Auth | JWT on the handshake; membership re-checked on each state-changing event (SRS NFR-SEC-05) |
| Back-pressure | Presence throttled to 1 event per 10 s per user; feed updates coalesced per 2 s per room |

### 7.4 Celery queues

| Queue | Jobs | Workers at R2 |
| --- | --- | --- |
| `poll` | Fallback polling tasks | 4 processes × 50 green threads (gevent) |
| `ingest` | Identity resolution, event writes, relays | 4 |
| `ml` | Taste vectors, suggestions, circles, model training | 2 (memory-heavy node) |
| `notify` | Push, email, digests | 2 |
| `default` | Recaps, battles, concerts, cleanup | 2 |

Fixed schedules (Celery Beat, Asia/Kolkata): battle phases Mon 18:00, Fri 18:00, Sun 21:00; recaps from 00:30 on the 1st; suggestions 03:00 nightly; circles Sunday 04:00; concert sync 05:00; purge jobs 02:00. All tasks are idempotent (keyed by entity and period) and retry at most 3 times with exponential backoff and jitter.

## 8. Scaling and capacity plan

At 5,000 concurrent users Jingle must absorb about 1,000 REST requests a second, 5,000 sockets and 20,000 listening events a minute; the plan below sizes each tier for twice that peak and names the test that proves it.

### 8.1 Load model (planning assumptions)

| Quantity | Value | Basis |
| --- | --- | --- |
| Peak concurrent users | 5,000 | SRS NFR-SCAL-01 |
| REST requests per active user | 0.2 per second | Feed refresh, card taps, sends; most live updates arrive over sockets |
| Peak REST load | 1,000 requests/s | 5,000 × 0.2 |
| Open sockets | 5,000 | One per active client |
| Listening events | 20,000 per minute | Push scrobbles, now-playing updates and polled listens at peak |
| Friends per user (median / p99) | 40 / 400 | Feed sizing |
| Read-to-write ratio | about 10:1 | Social-app norm; verify in beta |

### 8.2 Tier sizing for Release 2

| Tier | Unit capacity (to confirm in load tests) | Units at launch | Autoscale range | Scales on |
| --- | --- | --- | --- | --- |
| core-api (gunicorn + uvicorn workers) | about 250 simple requests/s per 2-vCPU pod with cached reads | 4 pods | 3–10 | CPU 60%, p95 latency |
| ingest-ml (uvicorn) | about 400 requests/s per 2-vCPU pod for I/O-bound calls | 2 pods | 2–6 | CPU, queue depth |
| realtime (Node) | about 2,000 idle-ish sockets per 1-vCPU pod at this event rate | 3 pods | 3–8 | socket count 1,700 per pod |
| Celery workers | see section 7.4 | 14 processes | 10–30 | queue lag over 30 s |
| PostgreSQL | 4 vCPU / 16 GB primary + 1 replica, PgBouncer transaction pooling (pool 100) | 1 + 1 | vertical | CPU 70%, connections 80% |
| MongoDB | 3-node replica set | 3 | vertical | write latency |
| Redis | 2 instances (cache, broker) with replicas | 2 + 2 | vertical | memory 70% |

The per-pod numbers are starting estimates; Sprint 10 load tests replace them with measured values, and HPA targets are then set from the measurements.

### 8.3 Keeping reads cheap

- **Feed:** friend cards come from Redis (`np:*` hashes and `feed:{user}` sorted sets); a feed request does one PostgreSQL query for the friend list (cached 5 min) and one Redis pipeline for up to 400 now-playing hashes.
- **Fan-out on read, pushed on write:** Jingle does not materialise every feed on each listen; a listen updates `np:{user}` and pushes to online friends' sockets. Offline friends build their feed on next open.
- **Django:** `select_related`/`prefetch_related` on every list endpoint; queries per request asserted in tests (no N+1); `CONN_MAX_AGE = 0` behind PgBouncer; server-side cursors disabled.
- **HTTP caching:** Cloudflare caches the landing page, static assets, public recap pages and artwork.

### 8.4 Load test plan (k6)

| Scenario | Shape | Pass criteria |
| --- | --- | --- |
| Ramp | 0 → 5,000 virtual users over 15 min, hold 30 min | Error rate < 0.5%; SRS NFR-PERF-01 to 04 met |
| Soak | 2,500 users for 4 hours | No memory growth over 10%; no queue lag |
| Spike | 1,000 → 5,000 in 60 s (battle reveal Sunday 21:00) | Autoscaling catches up within 3 min; p95 < 1 s during the spike |
| Session storm | 100 sessions × 50 members voting | Vote fan-out p95 ≤ 1 s |
| Source outage | Block Last.fm and ListenBrainz in staging | Cards degrade to cached Recent; no errors surfaced |

k6 runs from 2 load-generator nodes in the same region; WebSocket scenarios use k6's websockets module with Socket.IO framing.

### 8.5 Beyond 5,000

The first limits hit are PostgreSQL connections and Redis fan-out. The next steps, in order: more read replicas and read routing in Django; partitioning `recommendation_deliveries` and `session_votes` by month; moving domain events from Redis Streams to NATS JetStream; regional read caches.

## 9. Security, privacy, observability, failure modes and standards

Jingle protects third-party tokens as its most sensitive asset, measures itself against five SLOs, and has a written response for each of the eight failures most likely to hurt users.

### 9.1 Security design

| Asset or threat | Control |
| --- | --- |
| Platform tokens and scrobble tokens | Envelope encryption: AES-256-GCM data keys wrapped by a KMS key; decrypted only inside ingest-ml; key rotation yearly; never logged |
| Account takeover | Argon2id password hashing, optional TOTP 2FA, login rate limits, new-device email |
| Broken access control | Object-level permission checks in DRF (`has_object_permission`) with a shared policy module; tests for every endpoint's forbidden cases |
| Harassment and spam | 30 friend requests/day, report and block, moderation queue, suggestion guardrails |
| Injection and XSS | ORM-only queries, DRF serializers, React escaping, CSP with nonces |
| Upload abuse | Takeout files ≤ 50 MB, parsed in an isolated worker with streaming JSON, deleted within 24 h |
| Supply chain | Pinned dependencies, Dependabot, Trivy, signed images |

### 9.2 Privacy engineering (DPDP Act 2023 and Rules 2025)

- Consent records per purpose (`consents` table: purpose, version, given\_at, withdrawn\_at).
- Data export (`GET /me/export`) and deletion (`DELETE /me`) implemented as Celery workflows with audit entries.
- Minimisation: listens expire at 13 months; logs at 30 days; Spotify data within 24 h of unlinking.
- Breach runbook: notify the Data Protection Board and affected users without delay; full report within 72 hours.
- Age: 18+ at launch; verifiable parental consent flow (Rule 10) before under-18 sign-ups are opened.

### 9.3 Service level objectives

| SLO | Target (30-day window) | Error budget |
| --- | --- | --- |
| Availability of sign-in, feed, send, sessions | 99.5% | about 3.6 hours a month |
| Feed latency | 99% of requests under 800 ms server time | 1% |
| Live freshness | 95% of Live changes on friends' screens within 60 s | 5% |
| Vote fan-out | 95% within 1 s | 5% |
| False Live | 0 cards Live without a valid signal | None: any breach pages |

When an error budget is half spent, feature releases pause and the next sprint takes reliability work first.

### 9.4 Failure modes

| Failure | Detection | Automatic response | Human action |
| --- | --- | --- | --- |
| A bridge (Last.fm or ListenBrainz) is down | Adapter error rate > 20% for 5 min | Circuit breaker opens; cards show cached Recent with true time | Status page note |
| Rate limit exhausted | Token bucket empty | Skip polls; lengthen intervals | Review budget; push more users to push ingestion |
| Spotify revokes tester tokens | 401 on refresh | Mark source needs re-consent | Notify testers |
| Redis cache instance lost | Health checks | Feed falls back to PostgreSQL friend list + MongoDB latest listen | Restore replica |
| PostgreSQL primary fails | Managed failover | Promote replica (RTO ≤ 1 h) | Verify data, post-mortem |
| Celery backlog | Queue lag > 60 s | Autoscale workers | Find the slow task |
| Battle reveal spike | Socket and request surge Sunday 21:00 | Pre-scale at 20:45 via scheduled HPA floor | Watch dashboards |
| Bad model release | Suggestion acceptance drops by more than 30% day on day | Feature flag rolls back model version | Investigate in MLflow |

### 9.5 Runbooks

Each of these lives in `docs/runbooks/` with steps, commands and owners: source outage, token-key rotation, PostgreSQL failover and restore, Redis loss, queue backlog, data-deletion request, personal-data breach, abusive user escalation, Spotify allowlist change, and emergency feature disable.

### 9.6 Coding standards

| Area | Standard |
| --- | --- |
| Python | Python 3.12, Ruff (lint and format), mypy strict on ingest-ml and shared packages, pytest |
| TypeScript | Strict mode, ESLint, Prettier, Vitest |
| Commits | Conventional Commits; one story ID per pull request (`JNG-03-02: ...`) |
| Reviews | At least one approval; CI green; description links the story and its Gherkin scenarios |
| API | OpenAPI schema diff reviewed on every API change |
| Migrations | Backward-compatible (expand, migrate, contract) so rolling deploys never break |
| Docs | ADR for any change to a boundary, store or external dependency |

### Sources

- [ListenBrainz core API](https://listenbrainz.readthedocs.io/en/latest/users/api/core.html)
- [Last.fm API terms](https://www.last.fm/api/tos)
- [Spotify Developer Policy](https://developer.spotify.com/policy)
- [Spotify February 2026 migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide)
- [Google Data Portability API scopes](https://developers.google.com/data-portability/user-guide/scopes)
- [Ticketmaster Discovery API getting started](https://developer.ticketmaster.com/products-and-docs/apis/getting-started/)
