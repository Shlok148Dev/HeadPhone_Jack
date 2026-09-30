# Jingle — Integration Contracts (binding for every agent)

Owner: architect. Any change here needs an ADR and a note in `docs/office/STATE.md`.
Source: Technical Bible §1–4, §7, adjusted by `docs/adr/0001` (web-only zero-approval pilot) and `docs/adr/0002` (no route words).

## 1. Services, ports, origins

| Service | Dir | Port (container) | Public path via edge (Caddy, `http://127.0.0.1:8080`; `localhost:8080` also works but OAuth callbacks use 127.0.0.1) |
| --- | --- | --- | --- |
| edge (Caddy) | `infra/caddy/` | 8080 | — |
| web (Next.js) | `apps/web` | 3000 | `/` |
| core-api (Django + DRF) | `services/core_api` | 8000 | `/api/v1/*`, `/admin/*`, `/api/schema/*` |
| ingest-ml (FastAPI) | `services/ingest_ml` | 8001 | `/ingest/1/*` (ListenBrainz-compatible push) only |
| realtime (Node + Socket.IO) | `apps/realtime` | 4000 | `/rt/*` (Socket.IO `path: "/rt/socket.io"`) |
| workers (Celery worker + beat) | `services/core_api` image | — | — |
| demo-simulator | `services/ingest_ml` image | — | — (only when `JINGLE_DEMO=1`) |
| postgres 16 | — | 5432 | — |
| mongo 7 | — | 27017 | — |
| redis 7 | — | 6379 | — |
| qdrant | — | 6333 | — |

The browser talks to **one origin** (the edge). Refresh cookies are therefore first-party.

## 2. Ownership of storage (Technical Bible 1.1, refined by ADR-0006)

- Django owns **all migrations** (one migration history).
- core-api writes every business table.
- ingest-ml writes only the ingestion-domain tables: `platform_connections`, `linked_sources`, `scrobble_tokens`, `recordings`, `recording_links`, `artists`, `artist_tags`. It uses SQLAlchemy Core against the Django-created tables. core-api reads them.
- MongoDB `listens`, `provider_payloads`: written by ingest-ml. `notifications`: written by core-api.
- realtime never writes PostgreSQL.

## 3. Auth

- core-api issues JWTs: **access** (HS256, 15 min, `sub` = user UUID, `typ` = `access`, `iss` = `jingle-core`) returned in the JSON body and kept in memory by the web app; **refresh** in an HttpOnly, SameSite=Lax cookie `jingle_refresh`, path `/api/v1/auth`, rotated on use.
- Shared secret env `JWT_SIGNING_KEY`. realtime verifies access JWTs locally with `jose`.
- Service-to-service calls use header `X-Service-Token: $SERVICE_TOKEN` on `/internal/*` routes, which the edge never exposes.
- Scrobble (push) tokens: `Authorization: Token <scrobble-token>` exactly as ListenBrainz clients send it. Stored only as SHA-256 hash in `scrobble_tokens`.

## 4. Enumerations (identical spelling everywhere)

```
Platform     = SPOTIFY | APPLE_MUSIC | AMAZON_MUSIC | YOUTUBE_MUSIC | UNKNOWN
Via (route)  = DIRECT | LISTENBRAINZ | LASTFM | EXPORT | COMPANION        # internal only (BR-14)
SourceKind   = LISTENBRAINZ | LASTFM | APPLE_MUSIC | SPOTIFY | AMAZON_MUSIC | YOUTUBE_EXPORT | COMPANION
CardState    = LIVE | RECENT | TOP | HIDDEN
EventKind    = NOW_PLAYING | LISTEN
SourceStatus = CONNECTED | NEEDS_REAUTH | PENDING_FIRST_PLAY | ERROR | DISABLED
```

`COMPANION` is the Jingle Companion extension (and future Android app) pushing to `/ingest/1/*`. It is live-capable.
Live-capable routes: `COMPANION`, `LISTENBRAINZ`, `LASTFM`, `DIRECT` (Spotify only). Never `EXPORT`, never direct Apple/Amazon.

## 5. Normalised listening event (Technical Bible 2.4)

Published by ingest-ml to Redis Stream `events:listen` (field `data` = JSON) and stored in Mongo `listens` when `kind = LISTEN`.

```json
{
  "event_id": "uuid",
  "user_id": "uuid",
  "recording_id": "uuid | null",
  "raw": {"artist": "…", "title": "…", "album": "…", "duration_ms": 215000},
  "artwork_url": "https://… | null",
  "platform": "SPOTIFY",
  "via": "COMPANION",
  "kind": "NOW_PLAYING",
  "played_at": "2026-09-29T10:15:02Z",
  "observed_at": "2026-09-29T10:15:20Z",
  "trainable": true,
  "analytics_allowed": true,
  "played_at_estimated": false
}
```

`analytics_allowed = false` when `via` is `DIRECT` with platform `SPOTIFY` (Spotify Policy III.13, ADR-0013): such events feed only cards and the user's own history, never stats, scores, Blends, recaps or suggestions.

`trainable = false` when `via` is `DIRECT` with platform `SPOTIFY` (BR-03, Policy III.14) or `via` is `LASTFM` (BR-04).

## 6. Redis keys (Technical Bible 3.4 plus pilot additions)

| Key | Type | TTL | Writer | Purpose |
| --- | --- | --- | --- | --- |
| `np:{user_id}` | Hash: `event` (JSON of §5), `observed_at` (epoch s), `via`, `platform` | 90 s | ingest-ml | Live state. Absence ⇒ not Live |
| `last:{user_id}` | Hash, same fields as `np` for the newest LISTEN or NOW_PLAYING | none | ingest-ml | Recent state for the card |
| `presence:{user_id}` | String | 120 s | realtime | Adaptive polling |
| `rl:{source}` | token bucket | window | ingest-ml | Rate budgets |
| `sug:{user_id}` | JSON string | 24 h | workers | Precomputed suggestions |
| `sess:{id}:queue` / `sess:{id}:ver` | ZSET / counter | session life | core-api | Live queue |
| `flags:cache` | Hash | 30 s | core-api | Feature flags for other services |

Streams: `events:listen` (ingest → realtime, workers), `events:domain` (core-api → realtime: `feed.invalidate`, `notify`, `queue.delta`, `friendship.changed`, `block.created`). `notify.type` values: `friend_request`, `circle_invite`, `send`, `send_status`, `send_reaction` (ADR-0020).

## 7. FeedCard (SRS 5.5, amended by ADR-0002)

```json
{
  "friend": {"id": "uuid", "username": "aanya", "display_name": "Aanya", "avatar_url": null},
  "state": "LIVE",
  "platform": "SPOTIFY",
  "recording": {"id": "uuid|null", "title": "…", "artist": "…", "album": "…", "artwork_url": "…|null",
                 "links": {"SPOTIFY": "https://…", "APPLE_MUSIC": null}},
  "observed_at": "2026-09-29T10:15:20Z",
  "freshness_label": "Live on Spotify",
  "degraded": false,
  "attribution": null
}
```

- `via` is **not** sent to clients (BR-14). `attribution` is `"SPOTIFY"` only when the data came from the direct Spotify API (BR-03 attribution + link-back).
- `observed_at` omitted when the friend hides precise time (`freshness_label` then says e.g. "Recently on Spotify").
- Label grammar: `Live on {Platform}` | `Just now on {Platform}` | `Recently on {Platform}` (precise time hidden, or estimated time) | `{n} min ago on {Platform}` | `{n} h ago on {Platform}` | `{n} d ago on {Platform}` | `Top this month` | `Hidden`. Platform display names: Spotify, Apple Music, Amazon Music, YouTube Music; UNKNOWN ⇒ omit " on …".
- Card state resolution (BR-01/BR-02): LIVE iff `np:{u}` exists AND `now - observed_at < 90 s` AND `via` ∈ live-capable. Else RECENT from `last:{u}`. Else TOP from Mongo aggregation. Else HIDDEN if privacy hides activity (Private mode, not friends).

## 8. REST conventions (Technical Bible 4.1)

- Prefix `/api/v1/`; cursor pagination `?cursor=&limit=` (≤100) → `{"results": [], "next_cursor": null}`.
- Error envelope: `{"error": {"code": "SNAKE_UPPER", "message": "human text", "details": {}, "request_id": "…"}}`.
- `Idempotency-Key` header required on POST that creates sends, votes, nominations, queue adds.
- `X-Request-ID` accepted or generated at the edge; echoed on every response and in logs.

## 9. Socket.IO (`/rt`, Technical Bible 4.3)

Handshake: `auth: { token: <access JWT> }`. Rooms: `user:{id}`, `friends:{id}`, `circle:{id}`, `session:{id}`.
Server → client (ADR-0018: hints only): `feed:update {user_id}` → client refetches `GET /api/v1/feed/{user_id}`, `me:update`, `friends:changed`, `notify {type,id}`, `queue:state`, `queue:delta`.
Client → server: `session:join`, `queue:add`, `vote:cast` (forwarded to core-api `/internal/rt/*` which validates membership and writes).

## 10. Environment variables

See `.env.example` for the full list. Names are fixed; agents must not invent alternatives.

## 11. Companion pairing (web page ↔ extension)

Page: `{origin}/connect/companion` (web app). Extension content script runs only on that path of the configured origin.

1. Extension → page: `window.postMessage({type: "JINGLE_COMPANION_READY", version})`. Page may send `{type: "JINGLE_COMPANION_PING"}` to trigger READY.
2. User clicks "Connect this browser" → page calls `POST /api/v1/sources/companion/token` (JWT + CSRF-safe POST; never on page load, never from URL) → `{token}`.
3. Page → extension: `window.postMessage({type: "JINGLE_COMPANION_TOKEN", token}, location.origin)`; token = 8–512 printable ASCII, no spaces.
4. Extension validates via `GET /ingest/1/validate-token`, stores token in `chrome.storage.local`, replies `{type: "JINGLE_COMPANION_PAIRED", ok, userName?, error?}` with `error` ∈ `invalid_token | unreachable | wrong_origin | extension_error`.
5. Both sides accept messages only when `event.source === window` and `event.origin === location.origin`.
6. No READY within 3 s ⇒ page shows the token for manual paste and install instructions.
7. Page security (reviews/S2-EXT-security.md M3): strict CSP, no third-party scripts, `frame-ancestors 'none'`; token is ingest-scoped and revocable.
