# STATE — Jingle

_Last updated: 2026-09-29 (Sprint 0, block 1)_

## Current sprint
**Sprint 0 — Setup.** See `BOARD.md`.

## Done
- Read all five source documents (moved to `docs/source/`).
- `docs/PLAN.md`, `docs/architecture/CONTRACTS.md`, ADR-0001…0012.
- `.env.example`, `.gitignore`, `docs/office/HUMAN_ACTIONS.md`.

## Next
- Agents and skills in `.claude/`.
- Scaffold monorepo and Compose; launch parallel agents (research, UX spec, design system, services).

## Open risks
- R-A: Host already runs another project ("axis") on ports 5432/6379/6333/8025. Jingle publishes only the edge (8080) and never binds those ports.
- R-B: Heavy ML wheels (leidenalg, implicit, LightFM) may not build for Python 3.12 in slim images; mitigation: separate worker image target; LightFM optional (decide in S8).
- R-C: Spotify redirect URIs must use `127.0.0.1` (no `localhost`); callback is state-bound so it works across origins.

## Retros
(none yet)
