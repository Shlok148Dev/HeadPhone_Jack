# Last.fm API: bridge for Live and Recent

Checked: 2026-09-29. Owner: platform-researcher.

> Verification note: the `user.getRecentTracks` page and the API Terms of Service were read today (**verified**). Web-auth, error-code, top-items and Spotify-connection details are **inferred** (web tooling was rate-limited for part of the session); re-verify those before the S2 Last.fm adapter is merged.

## Question
How does Jingle read a user's now-playing, recent and top data from Last.fm, how does a user authorise it, and what do the terms allow? How does a Spotify user connect Spotify to Last.fm today?

## Impact (contradictions with CONTRACTS / ADRs / .env.example / source docs)

1. **Where the Spotify↔Last.fm link lives.** Tech Bible §2.5 says Jingle "opens Spotify's Last.fm link page". There is no such page inside the Spotify apps any more: the connection is made on **Last.fm's** site, Settings → Applications → "Spotify Scrobbling" → Connect (`https://www.last.fm/settings/applications`), which then shows Spotify's own consent screen. Onboarding copy and the deep link should target that Last.fm page. (inferred)
2. **Private listening data.** If the user enables "Hide recent listening" on Last.fm, `user.getRecentTracks` returns error **17** for unauthenticated calls. The adapter should prefer **web auth** (session key, `sk`) over "username only", because a signed call with the user's own session key can read their own data. `LASTFM_API_KEY`/`LASTFM_SHARED_SECRET` in `.env.example` are sufficient; no env change. (inferred)
3. **Live via Last.fm is conditional.** `nowplaying="true"` appears only if the scrobbling client sends `track.updateNowPlaying`. Spotify's built-in integration is believed to do so, but this must be confirmed in the S2 spike with a real account before LASTFM is treated as live-capable for Spotify on iPhone (CONTRACTS §4). (inferred)
4. **Budget number (verified).** Tech Bible 7.2 cites "about 5/s per IP"; the ToS (4.4) only says Last.fm "sets and enforces limits" with no number. Keep Jingle's 4 req/s bucket and treat error 29 as authoritative.
5. **Credit must be a button (verified).** ToS 2.7: "use one of the buttons saying 'powered by AudioScrobbler'", and links must point to the relevant Last.fm user/artist/album/track pages. ADR-0002 puts the credit on Settings → Connections only; whether one credit there satisfies 2.7 is a judgement call to record in an ADR. Using Last.fm's supplied button is licensed use (like Spotify's logo) and needs the same brand-rule exception.
6. **Permission for non-EEA users (verified).** ToS 2.8 requires explicit user permission to access their data for users outside the EEA. Jingle's pilot users are in India: the connect flow must include an explicit consent step even when linking by public username.

## Findings (verified where marked; otherwise inferred)

### Account and keys
- Create an API account at `https://www.last.fm/api/account/create` (free, instant, needs a Last.fm login). Yields **API key** and **shared secret**. Callback URL can be set there or passed per request as `cb`.
- Base: `https://ws.audioscrobbler.com/2.0/?method=...&api_key=...&format=json`.

### `user.getRecentTracks` (params, limit, nowplaying, no-auth: verified)
- Does **not** require authentication for public profiles.
- Params: `user` (required), `limit` (default 50, **max 200**), `page`, `from`/`to` (UNIX s, UTC), `extended` (0|1: adds artist info and `loved`), `api_key`; optional `sk` + `api_sig` for authenticated reads.
- Response `recenttracks.track[]`: `artist` (`#text`, `mbid`; with `extended=1` `name`, `url`, `image`), `name`, `mbid`, `album` (`#text`, `mbid`), `image[]` (`small|medium|large|extralarge`), `url`, `date` (`uts`, `#text`), `streamable`.
- Now playing: first item carries `"@attr": {"nowplaying": "true"}` and **no `date`**. Paging metadata in `recenttracks["@attr"]` (`page`, `perPage`, `totalPages`, `total`).
- Gotcha: a single-track result may be an object, not an array, in some legacy JSON responses; parse defensively.

```json
{"recenttracks":{"track":[
  {"artist":{"mbid":"","#text":"Arijit Singh"},"name":"Kesariya","mbid":"","album":{"mbid":"","#text":"Brahmastra"},
   "image":[{"size":"small","#text":"https://lastfm.freetls.fastly.net/i/u/34s/x.jpg"}],
   "url":"https://www.last.fm/music/Arijit+Singh/_/Kesariya","@attr":{"nowplaying":"true"}},
  {"artist":{"mbid":"","#text":"Prateek Kuhad"},"name":"cold/mess","mbid":"","album":{"mbid":"","#text":"cold/mess"},
   "date":{"uts":"1790676902","#text":"29 Sep 2026, 10:15"}}],
 "@attr":{"user":"aanya","page":"1","perPage":"50","totalPages":"120","total":"5999"}}}
```

### `user.getTopTracks` / `user.getTopArtists`
- Params: `user`, `period` = `overall|7day|1month|3month|6month|12month`, `limit` (default 50), `page`. Returns `toptracks.track[]` / `topartists.artist[]` with `playcount`, `mbid`, `@attr.rank`.

### Web authentication
1. Redirect the browser to `https://www.last.fm/api/auth/?api_key=KEY&cb=CALLBACK_URL`.
2. Last.fm redirects to `CALLBACK_URL?token=TOKEN` (token valid ~60 min, single use).
3. Server calls `auth.getSession` with `api_key`, `token`, `api_sig` → `session.key` (**does not expire** unless the user revokes), `session.name` (username).
- `auth.getToken` is for the desktop flow; the web flow does not need it.
- **api_sig** = `md5( concat of all params sorted by name as name+value, excluding format and callback, then + shared_secret )`, UTF-8, hex lowercase. Example for getSession: `md5("api_key" + KEY + "method" + "auth.getSession" + "token" + TOKEN + SECRET)`.
- The callback should be `https://<public host>/api/v1/sources/lastfm/callback` (Jingle-chosen; no Last.fm host restriction like Spotify's).

### Error codes
- 2 invalid service, 3 invalid method, 4 authentication failed, 6 invalid parameters (also "User not found"), 8 operation failed, 9 invalid session key (→ NEEDS_REAUTH), 10 invalid API key, 11 service offline, 13 invalid signature, 14 unauthorised token, 15 token expired, 16 temporary error (retry), **17 login required (private listening history)**, 26 suspended API key, **29 rate limit exceeded** (back off). HTTP status may be 200 or 4xx with `{"error":N,"message":"..."}`.

### Terms of Service (verified)
- 3.1: Last.fm Data "solely for non-commercial purposes"; commercial use needs a separate agreement.
- 4.3.4: "Reasonable Usage Cap" of **100 MB** of stored Last.fm Data; more needs written consent.
- 2.7: use one of the **"powered by AudioScrobbler"** buttons; link to the appropriate Last.fm pages.
- 2.8: privacy standards at least as strict as Last.fm's Privacy Policy; explicit permission for users outside the EEA.
- 4.4: rate limits enforced, not published.

### Spotify's built-in Last.fm scrobbling today (inferred)
- Set up on Last.fm web: **Settings → Applications → Spotify Scrobbling → Connect**, then approve on Spotify. There is no toggle inside current Spotify desktop or mobile apps (the old desktop "Social → Connect to Last.fm" setting was removed).
- Works server-side, so plays on every device (including iPhone) are scrobbled. Private sessions are not scrobbled. Now-playing is expected but must be spike-tested.

## Constraints for Jingle
- Last.fm events: `trainable = false` (BR-04); count toward the 100 MB cap (store normalised events, drop raw payload after resolution).
- 4 req/s total bucket; 60 s poll only while viewed.

## Sources (to re-verify)
- https://www.last.fm/api/show/user.getRecentTracks
- https://www.last.fm/api/show/user.getTopTracks
- https://www.last.fm/api/show/user.getTopArtists
- https://www.last.fm/api/webauth
- https://www.last.fm/api/authspec
- https://www.last.fm/api/errorcodes
- https://www.last.fm/api/tos
- https://www.last.fm/settings/applications
- https://support.last.fm/t/spotify-scrobbling/189
