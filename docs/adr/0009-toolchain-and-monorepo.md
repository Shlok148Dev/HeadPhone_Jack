# ADR-0009: Toolchain and monorepo mechanics

- Status: Accepted
- Date: 2026-09-29

- JavaScript: pnpm workspaces (`apps/*`, `packages/*`), Node 22 LTS, TypeScript strict. Next.js 15 App Router with React 19, Tailwind CSS v4, Motion, TanStack Query, Zustand, socket.io-client, openapi-typescript with openapi-fetch.
- Python: 3.12, uv per service (`services/core_api`, `services/ingest_ml`, `packages/py-common`), Ruff, mypy (strict on ingest-ml and py-common), pytest.
- Tests: pytest (with pytest-bdd for Gherkin), Vitest, Playwright with axe-core, k6.
- CI: GitHub Actions (`.github/workflows/ci.yml`).
- Layout follows Technical Bible 1.2 exactly, plus `apps/companion-extension` (kickoff §2) and `infra/caddy` (single-origin edge).
