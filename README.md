# Jingle

See what your friends are playing — on Spotify, Apple Music, YouTube Music and Amazon Music — share songs with a reason, and meet every week over music.

> Phase 1: web app, 10-user zero-approval pilot. Full quick start lands at the end of Sprint 1.

## Quick start (demo mode, no keys needed)

```bash
cp .env.example .env
docker compose up --build
```

Open <http://localhost:8080>.

## Repository

| Path | What |
| --- | --- |
| `apps/web` | Next.js web app and `/design` route |
| `apps/realtime` | Node + Socket.IO gateway |
| `apps/companion-extension` | Jingle Companion browser extension (MV3) |
| `services/core_api` | Django + DRF core API, Celery workers |
| `services/ingest_ml` | FastAPI ingestion, adapters, identity resolver |
| `packages/*` | Shared Python models, TypeScript client, design tokens |
| `docs/` | Plan, ADRs, contracts, research, UX spec, runbooks, office state |
