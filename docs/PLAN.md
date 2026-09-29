# Jingle — Engagement Plan (Phase 1: web pilot)

Owner: Orchestrator. Last updated 2026-09-29. This file carries the kickoff rules forward to every later session.

## 1. Mission and scope

Build Jingle, a cross-platform social layer for music listening, as a production-grade **web** app. Target: architecture fit for 1,000–5,000 concurrent users, first run as a **10-user pilot needing zero company approvals**, on one machine via Docker Compose. Mobile apps and store publishing are out of scope (ADR-0001).

## 2. Precedence of sources

Kickoff brief §2 (captured in ADR-0001…0003) > SRS v4.0 > Technical Bible > Technology Stack > Development Plan > PRD. Every conflict resolved is recorded in `docs/adr/`. Source documents live in `docs/source/`.

## 3. Hard rules (never break)

1. **No false Live (BR-01):** Live needs a now-playing signal < 90 s old from a live-capable route (`COMPANION`, `LISTENBRAINZ`, `LASTFM`, direct `SPOTIFY`).
2. **No scraping, no unofficial APIs** (no ytmusicapi, no reverse-engineered endpoints). Only official APIs, user-owned exports, bridges the user connects, and the Jingle extension reading pages the user has open.
3. **Spotify Developer Policy:** no ML training on Spotify API data; display-only, attributed; deleted within 24 h of unlinking (BR-03, ADR-0007).
4. **Secrets:** never commit keys; `.env` is git-ignored; `.env.example` is the template; never log secrets.
5. **No production credentials** in any agent session.
6. **Brand safety:** no copied logos, wordmarks, icons, fonts, exact layouts or artwork of Spotify, Apple Music, YouTube Music or Amazon Music. Platform names appear as text badges.
7. **Always runnable:** `docker compose up` works at the end of every sprint.
8. **Jingle Connect (BR-13–15):** one button per platform; no route words anywhere in the product (ADR-0002).
9. **Honest gaps:** phone listening on YouTube Music, Apple Music and Amazon Music shows Recent/history only in the web phase; never faked.

## 4. Operating model

- Orchestrator plans, delegates to specialist subagents (`.claude/agents/`), reviews, integrates, ships. Never waits for the founder.
- Project skills in `.claude/skills/` are invoked whenever a task matches.
- State lives in files: `docs/office/STATE.md` (source of truth for "where are we"), `BOARD.md`, `standups/`, `reviews/`, `HUMAN_ACTIONS.md`.
- Code work by agents happens in git worktrees; the Orchestrator merges one at a time and runs the test suite after each merge.
- Review gate: `code-reviewer` on every change; `security-privacy-reviewer` when auth or personal data is touched; `qa-engineer` confirms Gherkin scenarios; `design-system-engineer` approves UI screenshots (dark + light, 1440 px + 390 px).

## 5. Architecture summary

See `docs/architecture/CONTRACTS.md` (binding contracts) and ADRs. Services: web (Next.js), core-api (Django + DRF), ingest-ml (FastAPI), realtime (Node + Socket.IO), workers (Celery), plus PostgreSQL, MongoDB, Redis, Qdrant and a Caddy edge on `http://localhost:8080`.

## 6. Sprint plan (web phase)

Sprints are work blocks for the agent team, not calendar fortnights. Each ends with `docker compose up` green, STATE/BOARD updated and a retro.

| Sprint | Goal | Stories |
| --- | --- | --- |
| **S0 Setup** | Office, agents, skills, plan, monorepo scaffold per Tech Bible 1.2, Compose with all stores and services, CI, `/design` route with tokens and every card variant | JNG-13-06 (harness), design system |
| **S1 Accounts + ingest core** | Email + Google sign-in, 18+ gate, consents; push endpoint (ListenBrainz-compatible); scrobble tokens; identity resolver v1; own Live card; demo seed | JNG-01-01, 01-13, 01-10 (skeleton), 05-01 (own card), 05-08 |
| **S2 Jingle Connect** | Connection Orchestrator; ListenBrainz, Last.fm, direct-Spotify adapters with fixtures; Companion extension (YouTube Music, Spotify web, Apple Music web, Amazon Music web); YouTube Takeout import; flagged Apple/Amazon/Google adapters; onboarding | JNG-01-02…09, 01-11, 01-12, 01-14 |
| **S3 Social graph** | Search, requests, remove, block, report, privacy, Private mode, invite links/QR | JNG-02-01…07, 12-01 |
| **S4 Live feed** | Realtime gateway; Live/Recent/Top resolution; Live shelf; filter chips; degraded mode; open-in-my-app | JNG-05-01…08 |
| **S5 Suggestions** | Tech Bible §5 heuristic pipeline with reasons, dismiss, discoverability, cold start | JNG-03-01…03, 05…08 |
| **S6 Circles** | Circles, invites, roles, circle feed, Leiden suggested circles | JNG-04-01…08 |
| **S7 Sends** | Recommendations and mixtapes, delivery tracking, inbox, reactions | JNG-06-01…07 |
| **S8 Blends + sessions** | Blends with explanations; live sessions with votes, reconnect | JNG-07-01…09 |
| **S9 Understand** | Compatibility, stats, taste timeline | JNG-08-01, 02, 03, 06, 07 |
| **S10 Rituals + trust** | Weekly battles, monthly recap, notifications (in-app + web push), moderation console, flags/budgets admin, data export and deletion | JNG-09-01…06, 11-01…03, 11-07, 12-02…07, 13-04 |
| **S11 Hardening** | Security review, a11y pass, k6 smoke (50 users) + 5,000-user scripts, performance budgets, runbooks, final docs | EP-13 |

Concerts (EP-10) need a Ticketmaster key (free, no approval but a human signup); built behind `concerts_enabled` in S10 if capacity allows, else recorded as a gap.

## 7. Definition of Done (every ticket)

- Gherkin scenarios for the story pass as automated tests.
- Unit coverage of changed code ≥ 80%; type checks and linters clean.
- OpenAPI schema and TypeScript client regenerated if the API changed.
- Adapter changes pass contract tests against fixtures.
- UI changes screenshotted in both themes at 1440 px and 390 px and approved by design-system-engineer.
- code-reviewer approved; security-privacy-reviewer approved where relevant.
- `docker compose up` still works; STATE.md and BOARD.md updated.

## 8. Human actions

Only Shlok can do the items in `docs/office/HUMAN_ACTIONS.md`. Everything is built and tested against fixtures and demo mode; nothing blocks on them.

## 9. Resume prompt

> You are the Orchestrator of Jingle. Read docs/office/STATE.md, docs/office/BOARD.md and the latest file in docs/office/standups/, then continue exactly where the work stopped, following the kickoff rules in docs/PLAN.md and the agents and skills in .claude/. Do not ask questions; decide, record and proceed.

## 10. Token discipline (adopted 2026-09-29 at the founder's request; quality bar unchanged)

1. The Orchestrator builds shared, contract-heavy or small work itself; subagents get only isolated, well-bounded chunks with tight briefs.
2. Interrupted agents are **resumed** (SendMessage), never re-spawned.
3. One **combined** review agent per ticket (code + security checklist together). After fixes, the Orchestrator verifies the specific findings and reruns tests instead of a full re-review. A separate security-privacy-reviewer is used only for auth, token-handling or deletion flows.
4. Briefs name the exact files/sections to read ("CONTRACTS §5–7", not "all docs"); agents must not re-read source documents wholesale.
5. At most 2–3 concurrent agents.
6. Never grep/scan `node_modules`, `.venv`, or worktrees.
