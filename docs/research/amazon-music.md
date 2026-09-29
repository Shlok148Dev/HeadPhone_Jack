# Amazon Music Web API (V2)

Checked: 2026-09-29. Owner: platform-researcher.

> Verification note: web access hit a tooling session limit before this topic was fetched. **Findings are "inferred"** from Amazon's developer portal as known up to mid-2026. The adapter is flagged off (`amazon_music_enabled`, ADR-0001); nothing here blocks the pilot.

## Question
Is the Amazon Music Web API usable by Jingle, how is it authorised, and does it expose recently played?

## Impact (contradictions with CONTRACTS / ADRs / .env.example / source docs)

1. **An API key is needed besides OAuth.** Calls need both `Authorization: Bearer <LWA access token>` and `x-api-key: <security profile / API key>` issued after beta approval. `.env.example` has only `AMAZON_MUSIC_CLIENT_ID` and `AMAZON_MUSIC_CLIENT_SECRET`; an `AMAZON_MUSIC_API_KEY` would be needed when the flag is ever turned on. Architect decides (CONTRACTS §10 forbids agents inventing env names).
2. **No recently-played endpoint is publicly documented.** Consistent with SRS 4.2 ("Not documented"). The adapter's `recent()` and `now_playing()` must raise `NotSupported`; the declared capabilities are `live=false, recent=false, top=false, playlist_write=true` (library/playlists only). Tech Bible §2.2 "Library sync daily" is the only poll.

## Findings (all inferred)

### Status
- Web API V2 is a **closed beta**: developers apply through the Amazon Developer portal; access is granted case by case with a business-development review. Individuals without an agreement are generally not approved. Stays flagged off.

### Auth: Login with Amazon (LWA)
- Create an LWA security profile (client ID/secret) in the Amazon Developer Console; allowed return URLs must be HTTPS (localhost/loopback rules differ; confirm when relevant).
- Authorization code grant: `https://www.amazon.com/ap/oa?client_id&scope=profile%20amazon_music:access&response_type=code&redirect_uri&state` (PKCE supported via `code_challenge`), token at `POST https://api.amazon.com/auth/o2/token`. Access token ~1 h; refresh token long-lived.
- Music scope believed to be `amazon_music:access` (confirm).

### Endpoints (base `https://api.music.amazon.dev/v1`)
- `GET /me` (profile), `GET /me/playlists`, `POST /playlists`, `PUT/POST /playlists/{id}/tracks`, `GET /me/library/tracks|albums|artists`, `GET /tracks/{id}`, `GET /albums/{id}`, `GET /search`.
- Some tracks expose `isrc`.
- Recently played / now playing: **not in the V2 overview** (as of last knowledge).

### Terms
- Amazon Music API terms restrict storage of catalog data and require attribution/link-back to Amazon Music; exact clauses available only to approved developers.

## Constraints for Jingle
- Amazon Music Live comes only from the Companion on `music.amazon.*`; phone listening shows history only if the user also scrobbles elsewhere (PLAN rule 9, honest gaps).

## Sources (to re-verify)
- https://developer.amazon.com/docs/music/API_web_overview_v2.html
- https://developer.amazon.com/docs/music/API_web_auth.html
- https://developer.amazon.com/docs/login-with-amazon/authorization-code-grant.html
- https://developer.amazon.com/docs/music/API_web_reference.html
