# Web Scrobbler and the Jingle Companion (Manifest V3)

Checked: 2026-09-29. Owner: platform-researcher.

> Verification note: the licence and the ListenBrainz scrobbler source (`listenbrainz-scrobbler.ts`) were read today (**verified**). Connector internals and MV3 details are **inferred** (web tooling was rate-limited for part of the session); the extension-engineer should confirm each connector file before porting.

## Question
Can users point Web Scrobbler at Jingle, how do its connectors read the four web players, what may Jingle reuse, and what does MV3 require for our own extension?

## Impact (contradictions with CONTRACTS / ADRs / .env.example / source docs)

1. **Custom ListenBrainz URL is the full submit URL (verified).** The scrobbler uses `this.userApiUrl || 'https://api.listenbrainz.org/1/submit-listens'`, so the user must paste `http(s)://<host>/ingest/1/submit-listens`, not a base URL. It **never calls `validate-token`**: a wrong token only shows up as 401s on submit, so Jingle's "connected / pending first play" state must come from the first accepted submit (`PENDING_FIRST_PLAY` → `CONNECTED`).
2. **Web Scrobbler sends `playing_now` once per track.** Same Live-duration issue as in `listenbrainz.md` Impact 5: the card needs Live to last for the track's duration, not only 90 s from one ping. The Jingle Companion can avoid this by re-sending `playing_now` every ≤ 60 s while playback continues; recommend that as a Companion requirement.
3. **Extension → edge origin.** The Companion posts to `PUBLIC_BASE_URL`. MV3 needs that origin in `host_permissions`; with `http://localhost:8080` in dev and a different host in the pilot, the manifest needs both, or an optional host permission requested at runtime. No env change, but `apps/companion-extension` needs a build-time `PUBLIC_BASE_URL`.
4. **MIT attribution.** Forking or copying Web Scrobbler code requires keeping its copyright and licence notice in `apps/companion-extension` (e.g. `THIRD_PARTY_NOTICES`). Connector files are MIT-covered code; platform names/URLs in them are facts, not brand assets (fine under PLAN rule 6).

## Findings

### Licence (verified)
- Repository `web-scrobbler/web-scrobbler`, **MIT** licence. Copying requires including the copyright notice and permission notice.

### Custom endpoints (verified from source)
- README lists Last.fm, Libre.fm, ListenBrainz, Maloja, Pleroma. ListenBrainz takes a user token (`Authorization: Token …`) and an optional custom API URL (`userApiUrl`, full submit URL), so a user can send to Jingle with their **Jingle scrobble token**.
- `listen_type` values used: `playing_now`, `single`, `import`.
- `additional_info` sent: `submission_client: "Web Scrobbler"`, `submission_client_version`, `music_service_name` (connector label), `origin_url` (when available), `release_artist_name` (album artist), `spotify_id` (Spotify only), `duration` (seconds, when available). **No `music_service`, no `duration_ms`.** Jingle derives platform from `origin_url` host, then `music_service_name`.

### Connector approach (per site; inferred)
- A connector is a TypeScript file setting `Connector.playerSelector`, `artistSelector`, `trackSelector`, `albumSelector`, `trackArtSelector`, `isPlaying()`, `getUniqueID()`, `getCurrentTime()`, `getDuration()`, plus a `Connector.useMediaSessionApi()` helper that prefers `navigator.mediaSession.metadata` when present and falls back to selectors.
- **YouTube Music** (`music.youtube.com`, `youtube-music.ts`): DOM selectors on `ytmusic-player-bar` for title/byline/time plus Media Session for artwork/metadata; filters non-music videos by byline.
- **Spotify web player** (`open.spotify.com`, `spotify.ts`): DOM selectors on the now-playing bar (`data-testid` attributes) and play/pause button state; Media Session used as a fallback.
- **Apple Music web** (`music.apple.com`, `apple-music.ts`): mainly **Media Session** metadata (the player is inside shadow DOM web components), plus the audio element for time.
- **Amazon Music web** (`music.amazon.*`, `amazon.ts`/`amazon-music.ts`): DOM selectors on the player bar, Media Session where available.
- Selectors break when sites redesign; Media Session is the more stable primary source, DOM for play state, position and duration.

### Rules for the Jingle Companion (kickoff §3)
- Read only the pages the user has open, from the page itself (Media Session, DOM, the page's `<audio>/<video>` state). **No** calls to private platform endpoints, no reading cookies or tokens, no other users' data, no background fetching of platform pages.
- Send only to Jingle's `/ingest/1/submit-listens` with the user's scrobble token stored in `chrome.storage.local`.

### Manifest V3 constraints (inferred from Chrome docs)
- `"manifest_version": 3`; background is a **service worker** (`"background": {"service_worker": "sw.js", "type": "module"}`): no DOM, terminated after ~30 s idle, so keep no in-memory state; persist to `chrome.storage.session`/`local`. Use `chrome.alarms` (min period 30 s) for heartbeats.
- `content_scripts` with `matches`: `https://music.youtube.com/*`, `https://open.spotify.com/*`, `https://music.apple.com/*`, `https://music.amazon.com/*` (plus country domains such as `music.amazon.in`, `music.amazon.co.uk`). Media Session set by the page is readable from the isolated world in Chrome, but if not, inject a small script with `"world": "MAIN"` (Chrome 111+) and relay via `window.postMessage`.
- `host_permissions`: the four player origins (for content scripts) and the Jingle origin (for `fetch` from the service worker without CORS issues).
- `permissions`: `storage`, `alarms` (and `scripting` only if injecting programmatically). Avoid `tabs`/`<all_urls>`.
- Messaging: content script → `chrome.runtime.sendMessage` → service worker → `fetch` to Jingle. The worker debounces and dedupes by track ID.
- No remotely hosted code (MV3 policy); all JS bundled.
- Distribution: "Load unpacked" from `chrome://extensions` with Developer mode on; no Chrome Web Store listing needed for the pilot. Edge accepts the same package. Firefox would need `browser_specific_settings` and has MV3 differences (out of scope).

## Constraints for Jingle
- Companion events: `via = COMPANION`, live-capable, trainable (not Spotify API data, ADR-0007).
- Platform comes from the tab's origin, which is authoritative (better than `music_service`).

## Sources (to re-verify)
- https://github.com/web-scrobbler/web-scrobbler (LICENSE.md)
- https://github.com/web-scrobbler/web-scrobbler/tree/master/src/connectors
- https://github.com/web-scrobbler/web-scrobbler/wiki/Connectors-development
- https://github.com/web-scrobbler/web-scrobbler/blob/master/src/core/scrobbler/listenbrainz/listenbrainz-scrobbler.ts
- https://developer.chrome.com/docs/extensions/develop/migrate/what-is-mv3
- https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle
- https://developer.chrome.com/docs/extensions/reference/manifest/content-scripts
- https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions
- https://developer.mozilla.org/en-US/docs/Web/API/MediaSession/metadata
