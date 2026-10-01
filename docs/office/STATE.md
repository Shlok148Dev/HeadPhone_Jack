# STATE — Jingle

_Last updated: 2026-10-01 — **All sprints (S0–S11) complete.** Phase 1 (web pilot) is done._

## Final summary

### Complete and working (demo mode needs no keys: `docker compose up`, see README)
- **Accounts and data rights.**
  - Email sign-up and sign-in, plus Google sign-in once HA-3 is done. 18+ gate.
  - Privacy settings, Private mode, itemised consents.
  - Export of every domain as JSON, from the UI.
  - Account deletion: hidden now, purged within 30 days, shared circles, sessions and Blends handed over.
- **Jingle Connect.**
  - One button per platform, with invisible routing (ADR-0017).
  - Spotify: direct for up to 5 allowlisted users, Spotify's Last.fm link for everyone else, and the Companion on the web player.
  - YouTube Music, Apple Music and Amazon Music web players through the Companion extension (MV3, unpacked).
  - Last.fm and ListenBrainz connections; YouTube Takeout import.
  - Identity resolver; honest capability copy throughout.
- **Live feed.**
  - Live is never shown on a signal older than 90 s (BR-01).
  - Live, Recent and Top cards; realtime hints; honest degraded states.
  - Circle filter chips; Open in my app with a search fallback.
- **Social.** Friends, requests, blocks, reports, invite links + QR, and friend suggestions with ≤ 3 safe reasons (ADR-0019).
- **Circles.** Up to 50 members, roles, invites and 7-day links, circle feed, and Leiden suggested circles that never auto-join.
- **Sends.**
  - Tracks and 5–8 song mixtapes with notes.
  - Sent → Delivered → Viewed → Played, from the recipient's own listens.
  - Reactions, replies with a song, and discovery credits.
- **Blends** (with reasons and pins) and **live sessions** (shared queue, anonymous adds, one vote each with live re-order, host hand-over, rejoin).
- **Understand.**
  - Compatibility always shown with its breakdown (BR-09), and sound honestly "unavailable".
  - My stats and a 12-month timeline.
- **Rituals.**
  - Weekly battle per circle: nominate, 3 votes, late votes refused, results within 5 min, season table, skip week.
  - Monthly recap with a flip reveal, an opt-in share link and image export.
- **Notifications.** In-app centre, per-type controls, quiet hours, and opt-in web push (VAPID) capped at 5 a day.
- **Trust.**
  - Reports on users, circles and notes.
  - Staff console: queue with context, warn/mute/suspend/ban, appeals, audit log, feature flags, live per-source budgets, Spotify tester allowlist.
- **Quality bar.**
  - Gherkin scenarios from the SRS automated.
  - Unit coverage: core-api 93 %, ingest-ml 86 %, with each new app ≥ 86 %; realtime and web are covered by unit and E2E tests (no % gate configured).
  - E2E across EP-01…13, with axe WCAG 2.2 AA on every route in both themes.
  - Screenshots for both themes at 1440 and 390 px.
  - Security review approved (`reviews/S11-SECURITY-review.md`).
  - k6 smoke at 50 users: p95 73 ms, 0 errors.
  - Tested backup restore.

### Behind feature flags (off by default; built and tested against fixtures)
| Flag | What | Why off |
| --- | --- | --- |
| `apple_music_enabled` | Apple MusicKit direct route | needs Apple Developer enrolment |
| `amazon_music_enabled` | Amazon Music API route | needs Amazon API access |
| `google_dataportability_enabled` | Google Data Portability (YouTube history) | needs Google app verification; Takeout upload works now |
| `concerts_enabled` | Concerts (EP-10) | not built; needs a Ticketmaster key (HA-9) |
| `spotify_direct_enabled` (on) | Direct Spotify for ≤ 5 testers | works once HA-1 keys exist |

### Known gaps (accepted and shown honestly in the product)
- **No Live from phones** for YouTube Music, Apple Music or Amazon Music in the web phase. Those plays show as Recent and history (via Takeout, or Last.fm where the person scrobbles). Spotify phone listening is Live through Spotify's Last.fm link.
- **Spotify and Last.fm are not verified live** until HA-1 and HA-2 keys exist. They are covered by recorded fixtures and contract tests.
- **Compatibility "Sound"** stays unavailable: there is no audio analysis (Essentia) yet.
- **Saving a Blend to a platform** is reported as unavailable: there is no zero-approval write path.
- **Not built (Should/Could).** Concerts (EP-10), circles digest (JNG-09-09), email digest (JNG-11-05), comment threads (JNG-11-06), send streaks (JNG-09-07), timeline overlay and circle taste map (JNG-08-04/05), status page (JNG-13-08).
- **Scale.** The 5,000-user test and the NFR dashboards (JNG-13-01/02) are written and documented but need a staging environment. Zero-downtime deploys (JNG-13-05) need 2 replicas.
- **Staff accounts have no second factor.** Add TOTP before growing past the pilot.

### Recommended next phase
1. **Run the pilot.** Do HA-1, HA-2, HA-4 and HA-8 and invite the 10 people. Watch `/staff` → Budgets and the backup log for two weeks.
2. **Mobile apps (Phase 2).** An Android app that reads the phone's media session (Tech Bible 7.1) closes the biggest honest gap: Live from phones for YouTube Music, Apple Music and Amazon Music. iOS follows with MusicKit once Apple enrolment exists.
3. **Scale readiness.** Stand up staging with PgBouncer, run `infra/k6/scale-5000.js` and `session-storm.js`, add Grafana panels per NFR, and cache each owner's resolved feed signal.
4. **Approval-gated integrations.** Apple Music, Amazon Music, Google Data Portability and a Last.fm commercial agreement (BR-04).

## Done (on main)
### Sprint 11 — Hardening
- Security review: refresh-rotation race fixed (30 s grace, ADR-0011 addendum); Django admin closed at the edge, loopback bind by default, account deletion hands circles/sessions/Blends over (was cascading), full data export + UI (download, delete), refresh limit NAT-safe, postcss override; pnpm and pip audits clean.
- Accessibility pass: axe on every route in both themes + keyboard skip link/focus checks (`e2e/a11y.spec.ts`).
- Performance: k6 smoke 50 users (p95 73 ms, 0 errors); stress ceiling ~80 req/s at 0 errors; tuning record (uvicorn 4 workers, `DB_CONN_MAX_AGE=0`); 5,000-user + session-storm scripts.
- Backups: daily script, weekly tested restore (counts match), real-restore runbook.
- Docs: runbooks (operations, deploy-pilot with TLS overlay, backup-restore, incident, performance, scale-test), README, HUMAN_ACTIONS HA-8/HA-9, traceability EP-13.

### Sprint 0 — Setup
- Source docs in `docs/source/`; `docs/PLAN.md`, `docs/architecture/CONTRACTS.md`, ADR-0001…0016.
- 14 agent definitions, 6 project skills (no `frontend-design` skill installed; `jingle-design-system` + UX spec used instead).
- Monorepo per Tech Bible 1.2 (+ `apps/companion-extension`, `infra/caddy`); `docker-compose.yml` at root; CI workflow; research notes; UX spec.
- Design system: tokens, ds components, `/design` route (both themes, no overflow at 360/390 px).

### Sprint 1 — Accounts, ingest core, own Live card, demo
- core-api: email + Google sign-in (Google needs HA-3), 18+ gate, privacy + Private mode, itemised consents, export, deletion (erasure reaches ingest), feature flags, own-card resolver (BR-01/02/05, no `via`), Settings connections with honest notes, 10-char passwords, weak secrets refused outside local.
- ingest-ml: ListenBrainz-compatible push endpoint, identity resolver v1, dedupe, lineage flags, per-IP/per-user limits, safe link allowlist, user-data deletion, drain hook.
- Companion extension (MV3) for the four web players; pairing protocol (CONTRACTS §11).
- Demo mode: 13 personas (`jingle_common/demo.py`), `seed_demo`, `demo-simulator` service through the real push path; honest gaps preserved (ADR-0010 addendum).
- Web: landing, sign-up/sign-in, onboarding (profile → sources → privacy), Connect sheet (one button per platform, honest capability copy), `/connect/companion` pairing page (first-party-only CSP), AppShell (sidebar/rail/mobile tabs, my NowPlayingBar), Home (own card + no-friends empty state), Settings → Connections (credits and "How this works" only here), "Coming soon" pages for later sections; site-wide nonce CSP, `frame-ancestors 'none'`.
- Tests: py-common 8, ingest-ml ~140 (91% cov), core-api ~190 (97% cov), web unit 94, extension 74, Playwright E2E (JNG-01-01, JNG-05-01, screenshots dark/light × 1440/390 in `artifacts/screenshots/s1/`, axe on each tested page).
- Verified on the Compose stack: demo seed (13 users), simulator pushes all 200, demo login → Home shows own card with an honest label.

### Sprint 2 — Jingle Connect routes
- Connection Orchestrator (ADR-0017): one button per platform; Spotify direct (≤ 5 allowlisted, PKCE) → Spotify's Last.fm link → browser; others browser + flagged direct APIs. Missing keys never error (BR-15).
- Adapters with fixtures + contract tests: ListenBrainz, Last.fm (web auth + public username, `lastfm_link` consent), direct Spotify (display-only, purged on unlink), flagged Apple Music / Amazon Music / Google Data Portability.
- One write path for push, polling and exports (`ingest_ml/record.py`); poller via Celery beat (10 s) with per-source budgets and backoff; identity drain every 60 s.
- YouTube Takeout import (JSON + HTML, ≤ 50 MB, deleted after parsing); unlink (JNG-01-09); re-consent state (JNG-01-11).
- Web: Connect sheet runs the orchestrator plan (consent prompts, platform consent redirect, Last.fm → Spotify link step, browser steps, "Other ways to connect": ListenBrainz token, Last.fm username, Takeout upload with progress); Settings → Connections with Reconnect / Disconnect and return toasts; honest capability lines.
- Tests: ingest ~165 (86 % cov), core-api ~205 (97 % cov), web unit 94, E2E JNG-01-14 (2) green; review `docs/office/reviews/S2-CONNECT-review.md`.

### Sprint 3 — Social graph and privacy
- `social` app: friendships (ordered pair, merge on duplicate, 30/day), requests, remove, blocks (BR-07 both ways, silent), reports, search (username; display name only if discoverable), personal invite links + QR; policy helpers real; `/internal/users/{id}/friends` live; demo friendships seeded (11 friends + 1 pending).
- Web: Friends page (Friends / Requests / Find with invite QR), person menu (remove, block, report), invite landing `/invite/{code}` (remembered across sign-up), onboarding step 4 (friends), Settings → Privacy (visibility, Private mode, exact time, discoverability, blocked list) with settings sub-nav.
- Fix: "Only circles I choose" no longer lets plain friends see activity.
- Tests: social 12 (Gherkin JNG-02-03/04), E2E 9 green; review `docs/office/reviews/S3-SOCIAL-review.md`.

### Sprint 4 — Realtime gateway and friends' feed
- `GET /feed` + `GET /feed/{user}`: BR-02 ordering, Live filter, privacy/blocks, delayed flag, search fallback links (ADR-0018).
- Realtime gateway: JWT handshake, friend rooms, Redis Streams → coalesced hints, room re-sync on friendship/block changes, presence; adaptive polling in ingest.
- Home: Live now shelf, All/Live chips, everyone-else grid, degraded line, reconnect banner, my card; "Open in my app" honours my platform with search fallback.
- Tests: E2E 10 incl. live update without refresh; review `docs/office/reviews/S4-FEED-review.md`.

### Sprint 5 — Friend suggestions
- `jingle_ml` (ADR-0019): candidates → hard filters → Tech Bible 5.2 score → MMR diversify → ≤ 3 safe reasons; taste vectors from trainable listens + onboarding picks; Qdrant upsert; nightly + on-friendship + on-taste recompute on the ML worker; Redis cache; offline eval (demo: Recall@20 0.80, unsafe 0).
- API: `GET /suggestions` (read-time re-filtering), dismiss (90 days), `GET/PUT /me/taste`.
- Web: Suggestions tab, Home shelf, onboarding taste picker and suggestions. Demo: 3 new personas (2 friends-of-friends, 1 taste twin).
- Tests: suggestions 15 incl. Gherkin safety; E2E 11 green.

### Sprint 6 — Circles
- `circles` app: create (≤ 50 members under row lock, ≤ 20 per user), owner/admin/member, friend invites + 7-day hashed links, accept/decline, leave/remove/hand-over, settings (name, visibility, members-can-invite, battle schedule stored), circle feed, `/feed?circle=`; `share_circle` real; realtime watch list includes co-members.
- Suggested circles: Leiden weekly (Sun 04:00) on friend graph weighted by taste; 3–12 people, cohesive, not near an existing circle; creates only for the chooser, invites the rest (BR-08).
- Web: Circles list (create dialog, invitations, suggestions), circle page (ambient header, Live shelf, members with role actions, invite sheet with link, settings, leave/hand-over), `/circles/join/{token}`, Home circle chips. Demo: "KJ Somaiya crew", "Indie night".
- Retro: E2E caught a sticky `?invite=1` and demo-state drift (seed now resets the demo login's sandbox state). Home is at its 180 kB budget — S7 inbox must not add to Home's bundle.
- Tests: circles 10 incl. Gherkin (Full circle, never auto-join); E2E 14 green; review `docs/office/reviews/S6-CIRCLES-review.md`.

### Sprint 7 — Sends and mixtapes
- `sends` app (ADR-0020): track or 5–8 mixtape with a ≤ 280 note to friends and/or circles; Sent → Delivered → Viewed → Played (Played from the recipient's own analysable listens after the send); reactions and reply-with-a-song; daily discovery credits (Tech Bible 6.4); song search over known recordings; demo sends.
- Web: Send sheet (lazy) from any card and the Now Playing bar (recipient chips, mixtape builder, note counter), Inbox (Received/Sent, status chips, discovery credit, open on my platform with "Not found on {Platform}"), TopBar Inbox badge.
- Retro: optimistic close dropped `mutate` callbacks (use `mutateAsync` after unmount); `next/dynamic` cost 1 kB in the shared layout — `React.lazy` instead; Suggestions shelf now lazy, Home back to 180 kB.
- Tests: sends 12 incl. Gherkin JNG-06-03 (93 % cov), web unit 99, E2E 17; review `docs/office/reviews/S7-SENDS-review.md`.

### Sprint 8 — Blends and live sessions
- Blends (ADR-0021): Tech Bible 6.2 engine (group utility, 40 % share cap, 2 per artist, artist stand-in for LightFM), privacy gate (a member's plays count only if all others may see them), deterministic reasons, pins kept on regenerate, honest "save not available"; demo Blend.
- Live sessions: REST writes with idempotency keys, one ±1 vote each under a row lock, anonymous adds, versioned `queue.delta` broadcasts through realtime `session:{id}` rooms, presence + 30 s sweep for host hand-over, idle rooms end.
- Web: Blends list (+ Live sessions, Listen together), Blend detail (reasons, pin, regenerate, copy list), session room (Now, queue with votes, add song/anonymous, people, reconnect banner, host toasts), circle page "Make a Blend" / "Listen together".
- Retro: E2E proved live fan-out and 10 parallel votes on PostgreSQL; the privacy gate surfaced a real subtlety (a circle owner's default visibility hides their plays from non-friend members) — kept, and shown honestly.
- Tests: blends 10 + sessions 10 incl. Gherkin (91 % cov), realtime 9, web unit 102, E2E 26; review `docs/office/reviews/S8-BLENDS-SESSIONS-review.md`.

### Sprint 9 — Understand
- `insights` (ADR-0022): Tech Bible 6.1 compatibility (artists weighted Jaccard + genre cosine; sound honestly unavailable), monthly F_pairs recalibration, never without breakdown (BR-09); my stats after 14 days; 12-month timeline; profiles `GET /users/{username}`; demo genre tags.
- Web: `/u/[username]` (me: stats tiles, share bars, year timeline + sr table, building state; friend: CompatibilityMeter with notes and shared artists). Person names link to profiles.
- Fix: `AUTH_LOGIN_RATE` configurable (default 10/m; local 120/m); full-suite E2E sign-ins were being throttled.
- Retro: time-window code needs month-boundary-safe tests; Docker Desktop stopped mid-run again.
- Tests: insights 10 incl. Gherkin (96 % cov), E2E +2; review `docs/office/reviews/S9-UNDERSTAND-review.md`.

### Sprint 10 — Rituals, notifications, trust
- Rituals (ADR-0023): weekly battle per circle (schedule, nominate, 3 votes, anonymous voting, close job with results in under 5 min, skip week, 8-week season); monthly recap on the 1st/2nd with opt-in share link and canvas image.
- Notifications: one `notify()` for all events; in-app centre + bell; per-type controls; quiet hours; web push (VAPID, opt-in, 5/day cap) with a service worker.
- Trust: reports for users/circles/notes; staff console (queue with context, warn/mute/suspend/ban, appeals, audit log, flags, live source budgets, Spotify tester allowlist); mute/suspend enforced; demo moderator `mod@jingle.local`.
- Fixes: refresh/login rate limits configurable (refresh 120/m default); zero-width recap card; audit kwarg clash.
- Tests: rituals 8 incl. Gherkin, notifications 8, moderation 9, ingest usage 1 (91 % cov); E2E +3; review `docs/office/reviews/S10-RITUALS-TRUST-review.md`.

## Working mode
Founder directive: the Orchestrator does all work itself; subagents only when extremely necessary (PLAN §10 rule 0).

## Next
See "Recommended next phase" above.

<!-- previous next-steps kept below for history -->
1. Sprint 11 — hardening: security review, accessibility pass, k6 smoke (50 users) + 5,000-user scripts, performance budgets, runbooks, README quick start, pilot deployment guide, final STATE.

## Open risks
- R-A: Host runs another project ("axis") on 5432/6379/6333/8025; Jingle publishes only 8080.
- R-B: Heavy ML wheels (leidenalg) resolved in lock; LightFM decision deferred to S8.
- R-C: Spotify redirect must use 127.0.0.1; callbacks state-bound (ADR-0016).
- R-D: Docker Desktop on this host stops intermittently; restart it before `docker compose up`.
- R-F: Home route JS is at the 180 kB budget; new Home features must lazy-load.
- R-E (resolved S11): refresh-token rotation race fixed with a 30 s rotation grace (ADR-0011 addendum).

## Retros
### Sprint 11 (2026-10-01)
- Went well: a deliberate security pass found two real issues tests hadn't (cascade on owner deletion, exposed Django admin); measuring before tuning saved a bad change (threaded WSGI was slower).
- Watch: re-run the a11y + smoke specs before every pilot update.
### Sprint 10 (2026-10-01)
- Went well: one notify() entry point made prefs, quiet hours and caps apply everywhere at once; tests caught two real bugs before the UI did.
- Watch: shared-IP rate limits (pilot behind NAT); keep E2E self-healing when a run is interrupted.
### Sprint 9 (2026-10-01)
- Went well: honest-gap design (sound/genres unavailable) fell straight out of the formula.
- Watch: date math at boundaries; Docker Desktop stability.
### Sprint 8 (2026-09-30)
- Went well: hints + versioned state kept realtime simple; two-browser E2E caught nothing new — the design held.
- Watch: route JS for /blends 181 kB; review shared chunks in S11.
### Sprint 7 (2026-09-30)
- Went well: honest statuses fell out of existing lineage flags; the E2E caught a duplicate accessible name and a dropped toast.
- Watch: shared layout JS creeps (friends 182 kB); keep new chrome tiny.
### Sprint 6 (2026-09-30)
- Went well: row lock + check constraint made the 50 limit safe; Gherkin covered the SRS scenarios directly.
- Watch: containers must be rebuilt after backend commits before E2E (stale core-api cost one run).
### Sprint 5 (2026-09-30)
- Went well: pure pipeline made the SRS safety scenarios exact unit tests; computing on the worker kept the API image light.
- Watch: coverage metric needs a larger world; JS budget on Home.
### Sprint 4 (2026-09-30)
- Went well: hint-based realtime kept privacy in one place; the E2E proved live updates arrive in seconds.
- Watch: run a11y on settled UI; keep an eye on the 180 kB home budget (177 kB now).
### Sprint 3 (2026-09-30)
- Went well: rules centralised in services/policy made the Gherkin block scenario straightforward.
- Watch: E2E tests must not depend on mutable demo state; tests now create their own data.
### Sprint 2 (2026-09-30)
- Went well: one shared write path made every new route inherit dedupe, lineage and BR-01; fixture-based contract tests caught a too-tight Apple budget and a wrong-encoding file.
- Watch: always write files as UTF-8 (a cp1252 write truncated one file; restored from git). Presence-based polling still pending.

### Sprint 0 + 1 (2026-09-29)
- Went well: contracts + ADRs up front made parallel work mergeable; reviews caught real bugs (false-Live heartbeat, phishing links, duplicate listens, weak secrets).
- Went badly: six parallel agents plus double reviews burned ~1.6M tokens and hit usage limits twice.
- Change: Orchestrator builds directly, one combined review done by the Orchestrator against the reviewer checklists, subagents only when necessary.
