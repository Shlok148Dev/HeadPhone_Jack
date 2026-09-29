# STATE — Jingle

_Last updated: 2026-09-29 evening (Sprint 0/1 integration)_

## Current sprint
**Sprint 0 — Setup** (overlapping with Sprint 1/2 work). See `BOARD.md`.

## Done (on main)
- Source docs moved to `docs/source/`; `docs/PLAN.md`, `docs/architecture/CONTRACTS.md`, ADR-0001…0012.
- 14 agents in `.claude/agents/`, 6 project skills in `.claude/skills/`. No `frontend-design` skill is installed; frontend agents use `jingle-design-system` + UX spec instead.
- Monorepo scaffold (Tech Bible 1.2 layout + `apps/companion-extension`, `infra/caddy`); `docker-compose.yml` at root; all 11 containers healthy; edge on http://localhost:8080 (verified `/api/v1/ping`, web 200).
- py-common (enums, events + training lineage, AES-256-GCM envelope crypto, labels, JSON logging) with tests; core-api + ingest-ml skeletons with tests; ingestion-domain tables (sources app); CI workflow; `.gitattributes` LF.

## Merged to main
- S2-EXT Companion extension (code + security approved; 74 tests).

## In flight (resumed after 2nd rate limit; lean mode, PLAN §10)
- ingest-engineer: S1-INGEST review fixes (H1 links, dedupe, username, lineage flags, per-IP limit, deletion endpoint).
- design-system-engineer: S0-09 finishing /design overflow fix.
- security-privacy-reviewer: combined review of S1-CORE (branch s1-backend-core-api).
- Pending for backend after review: M6 refuse default secrets; call ingest `DELETE /internal/users/{id}/data` on deletion/withdrawal.

## Next (on resume)
1. For each worktree branch: review (code-reviewer; security-privacy-reviewer for backend/ingest/extension), then merge into main one at a time, run all tests, `docker compose up --build` check.
2. Read research Impact sections; write ADRs for any contract changes.
3. Then: demo seed + simulator (ADR-0010), S2 adapters (ListenBrainz, Last.fm, Spotify direct) + Connection Orchestrator + onboarding web screens, realtime gateway.

## Open risks
- R-A: Host runs another project ("axis") on 5432/6379/6333/8025; Jingle publishes only 8080.
- R-B: Heavy ML wheels in worker image (leidenalg etc.) — resolved in lock; LightFM decision deferred to S8.
- R-C: Spotify redirect URIs must use 127.0.0.1; callback must be state-bound.

## Retros
(none yet)
