# STATE — Jingle

_Last updated: 2026-09-29 night — Sprint 1 complete (pending final E2E rerun, see "Next" 1)_

## Current sprint
**Sprint 1 done.** Next: **Sprint 2 — Jingle Connect routes** (see `BOARD.md`).

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

## Working mode
Founder directive: the Orchestrator does all work itself; subagents only when extremely necessary (PLAN §10 rule 0).

## Next
1. Rerun `npx playwright test` after the toast-region a11y fix (`role="region"` in `ds/Toast.tsx`), rebuild web, review screenshots; commit.
2. Sprint 2: Connection Orchestrator; ListenBrainz + Last.fm (web auth, consent `lastfm_link`) + direct Spotify (PKCE, allowlist, 403 fallback, 24 h deletion) adapters with fixtures and contract tests; poll tasks via Celery → ingest `/internal/poll/*`; YouTube Takeout import (JSON + HTML); flagged Apple/Amazon/Google adapters; re-consent notices (JNG-01-11); unlink (JNG-01-09); Connect sheet "Other ways to connect" becomes real; schedule `/internal/identity/drain`.
3. Sprint 3: friends, blocks, reports, privacy UI, invite links; seed demo friendships.

## Open risks
- R-A: Host runs another project ("axis") on 5432/6379/6333/8025; Jingle publishes only 8080.
- R-B: Heavy ML wheels (leidenalg) resolved in lock; LightFM decision deferred to S8.
- R-C: Spotify redirect must use 127.0.0.1; callbacks state-bound (ADR-0016).
- R-D: Docker Desktop on this host stops intermittently; restart it before `docker compose up`.
- R-E: Refresh-token rotation can race across two open tabs (second tab is signed out); acceptable for pilot, revisit with a grace window in S11.

## Retros
### Sprint 0 + 1 (2026-09-29)
- Went well: contracts + ADRs up front made parallel work mergeable; reviews caught real bugs (false-Live heartbeat, phishing links, duplicate listens, weak secrets).
- Went badly: six parallel agents plus double reviews burned ~1.6M tokens and hit usage limits twice.
- Change: Orchestrator builds directly, one combined review done by the Orchestrator against the reviewer checklists, subagents only when necessary.
