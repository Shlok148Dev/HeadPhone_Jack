# STATE — Jingle

_Last updated: 2026-09-30 — Sprint 4 complete_

## Current sprint
**Sprints 0–4 done.** Next: **Sprint 5 — friend suggestions** (see `BOARD.md`).

## Done (on main)
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

## Working mode
Founder directive: the Orchestrator does all work itself; subagents only when extremely necessary (PLAN §10 rule 0).

## Next
1. Sprint 5 — friend suggestions (Tech Bible §5): candidates (friends of friends, taste neighbours, shared context, same college/city), hard filters (blocks, discoverability, 90-day dismiss, adult–minor), heuristic score (Adamic–Adar + taste cosine + context + local), diversify, ≤ 3 reasons without leaking private listening; nightly + on-new-friend Celery job; `GET /suggestions`, dismiss; Friends/Home UI; cold-start genre picker.
2. Sprint 6 — circles, invites, roles, circle feed + chips, Leiden suggested circles.

## Open risks
- R-A: Host runs another project ("axis") on 5432/6379/6333/8025; Jingle publishes only 8080.
- R-B: Heavy ML wheels (leidenalg) resolved in lock; LightFM decision deferred to S8.
- R-C: Spotify redirect must use 127.0.0.1; callbacks state-bound (ADR-0016).
- R-D: Docker Desktop on this host stops intermittently; restart it before `docker compose up`.
- R-E: Refresh-token rotation can race across two open tabs (second tab is signed out); acceptable for pilot, revisit with a grace window in S11.

## Retros
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
