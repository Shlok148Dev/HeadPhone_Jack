# Jingle

See what your friends are playing — on Spotify, Apple Music, YouTube Music and Amazon Music — share songs with a reason, and meet every week over music.

> Phase 1: web app, 10-user zero-approval pilot. Status and roadmap: [`docs/office/STATE.md`](docs/office/STATE.md), plan: [`docs/PLAN.md`](docs/PLAN.md).

## 5-minute quick start (demo mode, no keys needed)

Requirements: Docker Desktop (or Docker Engine + Compose v2).

```bash
cp .env.example .env
```

```bash
docker compose up --build
```

Open <http://127.0.0.1:8080> (use `127.0.0.1`, not `localhost`: Spotify's sign-in redirect needs it).

Demo mode (`JINGLE_DEMO=1`, the default in `.env.example`) seeds 12 fake friends across all four platforms and a simulator that plays music through the real ingestion pipeline. Sign in with:

| Email | Password |
| --- | --- |
| `demo@jingle.local` | `jingle-demo-2026` (demo only; override with `DEMO_PASSWORD`) |

Your own card on Home goes Live whenever the simulator "plays" for the demo account.

### Load the Jingle Companion (browser extension)

The Companion shares what **you** play in the Spotify, Apple Music, YouTube Music and Amazon Music web players with your Jingle account, and nothing else.

```bash
pnpm install
```

```bash
pnpm --filter @jingle/companion-extension build
```

Then in Chrome or Edge: `chrome://extensions` → **Developer mode** → **Load unpacked** → choose `apps/companion-extension/dist`. In Jingle go to **Settings → Your music apps → Connect**, press **Connect this browser**, and play a song in a web player.

## What only the founder can do

Real Spotify, Last.fm and Google keys, and production secrets: see [`docs/office/HUMAN_ACTIONS.md`](docs/office/HUMAN_ACTIONS.md). Everything works without them in demo mode.

## Development

| Task | Command |
| --- | --- |
| Web unit tests | `pnpm --filter @jingle/web test` |
| Web E2E + a11y + screenshots (stack running) | `cd apps/web && npx playwright test` |
| core-api tests | `cd services/core_api && uv run pytest` |
| ingest-ml tests | `cd services/ingest_ml && uv run pytest` |
| Regenerate API schema + TS client | `cd services/core_api && uv run python manage.py spectacular --file openapi.yaml` then `pnpm --filter @jingle/ts-client generate` |

## Repository

| Path | What |
| --- | --- |
| `apps/web` | Next.js web app and `/design` route |
| `apps/realtime` | Node + Socket.IO gateway |
| `apps/companion-extension` | Jingle Companion browser extension (MV3) |
| `services/core_api` | Django + DRF core API, Celery workers, demo seed |
| `services/ingest_ml` | FastAPI ingestion, identity resolver, demo simulator |
| `packages/*` | Shared Python models, TypeScript client, design tokens |
| `docs/` | Plan, ADRs, contracts, research, UX spec, office state, traceability |

Platform names are trademarks of their owners. Jingle is not affiliated with Spotify, Apple, Google or Amazon.
