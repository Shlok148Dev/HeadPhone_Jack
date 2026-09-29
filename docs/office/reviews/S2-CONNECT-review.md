# S2 Jingle Connect — combined review (Orchestrator, against code, security and design checklists)

Scope: ingest `record.py`, adapters (ListenBrainz, Last.fm, Spotify, flagged Apple/Amazon/Google), orchestrator, poller, connect/import API; core-api connect views, tasks, consents; web Connect sheet and Settings → Connections.

- Contracts: one write path for all routes; `via` never leaves the server; lineage flags on every stored listen; BR-01 enforced by type (`NowPlaying.from_adapter`); exports never write `np:`.
- Security: OAuth state single-use (GETDEL) + PKCE S256; callbacks redirect only to `PUBLIC_BASE_URL` (no open redirect); platform tokens sealed with AES-256-GCM bound to the user (AAD); weak/dev KEK refused outside local/test; uploads ≤ 50 MB, content-sniffed, deleted after parsing; import jobs private per user; `/internal/*` service-token only; Spotify data purged on unlink/withdrawal; consent gates (`activity_sharing`, `lastfm_link`) enforced server-side.
- Resilience: ≤ 3 attempts with backoff + jitter, Retry-After honoured, budgets per source; failures reschedule instead of erroring cards.
- Tests: ingest contract tests (25) against fixtures + existing suite (86 % cov); core-api connect tests (17), 97 % cov; web unit 94; E2E JNG-01-14 (YouTube consent → browser steps → Takeout import → connected → disconnect; Spotify without keys → browser path, no error).
- Known limits: Spotify/Last.fm live flows verified with fixtures only until HA-1/HA-2 keys exist; adaptive (presence-based) polling waits for Sprint 4.

VERDICT: APPROVED
