# Apple Music API and MusicKit JS v3

Checked: 2026-09-29. Owner: platform-researcher.

> Verification note: web access hit a tooling session limit before this topic was fetched. **Findings are "inferred"** from Apple's Apple Music API and MusicKit JS documentation as known up to mid-2026. The adapter is flagged off (`apple_music_enabled`, ADR-0001), so re-verify before the flag is turned on.

## Question
How does the web app authorise Apple Music and read recent plays, heavy rotation, ISRC and artwork?

## Impact (contradictions with CONTRACTS / ADRs / .env.example / source docs)

1. **Recently played has no timestamps.** `/v1/me/recent/played/tracks` returns an ordered list of songs without `played_at`. CONTRACTS §5 requires `played_at`, and card labels need "n min ago". The adapter can only diff successive polls and stamp new items with `observed_at` (an upper bound), so Apple-direct recents should be labelled as "Recently on Apple Music" (precise time hidden) or carry a flag such as `played_at_estimated`. ADR needed.
2. **Recents depth is small.** Only about the last few dozen tracks are reachable (see limits), so a 10-minute poll can miss plays for heavy listeners; the gap must be accepted, not backfilled.
3. **Developer-token lifetime.** Tech Bible §2.2 "rotated every 90 days" is fine; the hard maximum `exp` is ~6 months (15,777,000 s). `.env.example` names (`APPLE_MUSIC_TEAM_ID`, `APPLE_MUSIC_KEY_ID`, `APPLE_MUSIC_PRIVATE_KEY_PATH`) match what is needed. No change.
4. **Requires the paid Apple Developer Program** (to create a MusicKit key). Consistent with ADR-0001: stays flagged off for the pilot.

## Findings (all inferred)

### Developer token
- JWT signed **ES256** with a MusicKit private key (`.p8`) from Certificates, Identifiers & Profiles → Keys (MusicKit enabled).
- Header: `{"alg":"ES256","kid":"<APPLE_MUSIC_KEY_ID>"}`. Claims: `{"iss":"<APPLE_MUSIC_TEAM_ID>","iat":<now>,"exp":<≤ now+15777000>}`; optional `"origin":["https://jingle.example"]` to restrict web use.
- Sent as `Authorization: Bearer <developer token>` to `https://api.music.apple.com`.

### Music User Token (web)
- Load `https://js-cdn.music.apple.com/musickit/v3/musickit.js`; `await MusicKit.configure({developerToken, app:{name:"Jingle", build:"0.1"}})`; `const mut = await MusicKit.getInstance().authorize()` shows Apple's sign-in/consent popup.
- Send the MUT to core-api → ingest-ml, stored encrypted. Requests add header `Music-User-Token: <mut>`. Lifetime is not documented (months); 401/403 → NEEDS_REAUTH, refreshed on next visit via `authorize()`.
- The user needs an active Apple Music subscription for library/history endpoints.

### Endpoints
- `GET /v1/me/recent/played/tracks?limit=<1..30>&offset=` → `data[]` of `songs` (or `library-songs`) resources; default limit 10, max 30 per page, total reachable history small (~50). No timestamps.
- `GET /v1/me/history/heavy-rotation?limit≤10` → albums/playlists/stations the user plays often (not tracks).
- `GET /v1/me/recent/played?types=` → recently played containers (albums, playlists, stations).
- `GET /v1/me/storefront` → user's storefront id (e.g. `in`), needed for catalog calls.
- ISRC lookup: `GET /v1/catalog/{storefront}/songs?filter[isrc]=INS181900123` → `data[]` songs; many-to-one (several catalog IDs can share an ISRC). A song's `attributes.isrc` gives ISRC in the other direction.
- Song attributes used: `name`, `artistName`, `albumName`, `durationInMillis`, `isrc`, `url` (music.apple.com link for "Open in my app"), `artwork`.

### Artwork
- `attributes.artwork = {"url":"https://is1-ssl.mzstatic.com/image/thumb/.../{w}x{h}bb.jpg","width":3000,"height":3000,"bgColor":"...","textColor1":"..."}`. Replace `{w}` and `{h}` (e.g. `300x300`). Some templates also have `{f}` for format (`jpg`/`webp`).

### Rate limits
- Not published; Apple throttles with `429`. Keep ≤ 1 req/s per user (Tech Bible 7.2).

## Constraints for Jingle
- Never Live (BR-01): direct Apple Music has no now-playing endpoint. Live comes only from the Companion on music.apple.com.
- Apple Media Services terms: display artwork/metadata with link back to Apple Music; no "Apple Music" logo copying (PLAN rule 6); use text badge.

## Sources (to re-verify)
- https://developer.apple.com/documentation/applemusicapi/generating-developer-tokens
- https://developer.apple.com/documentation/applemusicapi/user-authentication-for-musickit
- https://developer.apple.com/documentation/musickitjs
- https://developer.apple.com/documentation/applemusicapi/get-recently-played-tracks
- https://developer.apple.com/documentation/applemusicapi/get-heavy-rotation-content
- https://developer.apple.com/documentation/applemusicapi/get-multiple-catalog-songs-by-isrc
- https://developer.apple.com/documentation/applemusicapi/artwork
- https://developer.apple.com/programs/
