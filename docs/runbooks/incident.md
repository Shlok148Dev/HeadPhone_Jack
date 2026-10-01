# Incidents: symptoms → checks → fixes

| Symptom | Check | Fix |
| --- | --- | --- |
| Qdrant exits at start: `Failed to load local shard … EOF while parsing` | `docker compose logs qdrant` (unclean Docker stop corrupted a collection) | Vectors are derived data: remove the named collection (`docker run --rm -v jingle_qdrantdata:/s alpine rm -rf /s/collections/<name>`), `docker compose up -d`; the next suggestions run rebuilds it |
| Whole app down locally | `docker compose ps`; "cannot connect to the Docker API" | Start Docker Desktop, wait for "running", then `docker compose up -d` (R-D: it stops on this host from time to time) |
| Cards show "Reconnecting…" | `docker compose logs realtime` | Restart realtime. Cards keep their last honest state, and polling covers in the meantime (ADR-0018) |
| Nobody goes Live | Redis up? `docker compose exec redis redis-cli ping`; ingest logs for push 4xx | Restart ingest-ml. Live needs a signal under 90 s old, so this resolves on the next play (BR-01) |
| One source silent (e.g. Last.fm) | `/staff` → Budgets: refused counts; ingest logs `BudgetExhausted` / 429 | The budget is protecting the source. Polling backs off on its own. Raise the budget only within the platform's published limits |
| "Too many requests" for normal use | core-api logs `RATE_LIMITED` scope | Pilot users behind one NAT share an IP. Check `AUTH_REFRESH_RATE` (default 120/m) |
| `FATAL: sorry, too many clients` | `docker compose logs core-api` | Keep `DB_CONN_MAX_AGE=0` without PgBouncer, or lower `WEB_CONCURRENCY` |
| Feed empty with "delayed" | Mongo up? `docker compose ps mongo` | Restart mongo. The feed degrades to the cached state honestly (JNG-05-07) |
| Spotify direct route stopped | User sees "Reconnect" | The user reconnects. Check the allowlist in `/staff` (max 5, Spotify development mode) |
| Push not arriving | `/settings/notifications` says available? VAPID keys in `.env`? Quiet hours or the 5/day cap? | Generate keys (operations.md) and restart core-api and workers |
| Account wrongly actioned | `/staff` → Audit log | Overturn via the person's appeal, or act again with a note |
| Suspected leak of a secret | — | Rotate it (operations.md → Secrets). Rotate `SERVICE_TOKEN` across all services together. For a KEK leak, re-encrypt by reconnecting sources |

When in doubt, `docker compose restart <service>` is safe. Every service is stateless apart from the databases.
