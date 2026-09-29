# Jingle Companion (browser extension, Manifest V3)

Shares what **you** are playing in the YouTube Music, Spotify, Apple Music and Amazon Music web players open in this browser with **your own Jingle server**, so your friends see you "Live" and your history fills in. Chrome and Edge (≥ 120). Ticket JNG-01-14 (capture side); see `docs/adr/0003-companion-push-first-ingestion.md`.

## What it captures

Only from the four web player tabs you have open:

| Player | Hosts | Signal |
| --- | --- | --- |
| YouTube Music | `music.youtube.com` | MediaSession metadata + page `<video>`; player-bar title/byline only if MediaSession is empty; ads skipped |
| Spotify | `open.spotify.com` | MediaSession metadata/playbackState; position/duration from the player-bar clock (its media element is not in the DOM) |
| Apple Music | `music.apple.com` | MediaSession + page `<audio>` |
| Amazon Music | `music.amazon.{com,in,co.uk,de,fr,it,es,ca,com.au,co.jp,com.br,com.mx}` (regional copies of the same web player) | MediaSession + page media element |

Primary signal is always the standard `navigator.mediaSession.metadata` / `playbackState` and the page's own media element (`currentTime`, `duration`, `paused`). DOM selectors are a small, per-site fallback in `src/connectors/*.ts`, covered by hand-written fixtures in `tests/fixtures/`. The extension never calls any platform API or private endpoint and never reads anyone else's data.

## Privacy

- **Sends only to your Jingle server** (the address in the popup; default `http://localhost:8080`). No analytics, no third parties.
- Fields sent (ListenBrainz format, `POST {origin}/ingest/1/submit-listens`, `Authorization: Token <your token>`): artist, track title, album (if known), and `additional_info` = `music_service` (player host), `origin_url` (link to the track, when the page exposes one), `duration_ms`, `submission_client` = "Jingle Companion", `submission_client_version`. Finished listens also carry `listened_at` (start time).
- Nothing is sent while **Pause sharing** is on, for players you switched off, or before you sign in.
- The token is stored only in `chrome.storage.local`, never logged, and is removed on sign-out or when you change the server address.
- Permissions: `storage`, `alarms`; host access to the four players and `localhost:8080` / `127.0.0.1:8080`. A custom Jingle address (https) is requested at runtime for that one origin only, together with `scripting` so the pairing page can hand over the token.

## Scrobble rules

- `playing_now` when a track starts or resumes, then every 30 s while playing (keeps Jingle's 90 s Live window fresh). Nothing while paused or after the tab closes, so Jingle naturally falls back to Recent.
- One `single` per play once you have **listened** to ≥ 50% of the track or 4 min (whichever is first); never for tracks shorter than 30 s. Seeking forward does not count as listening; replaying a finished track counts again.
- `single` listens that fail (offline, server down, token rejected) wait in an offline queue (max 500, retry 30 s → 1 h backoff). `playing_now` is never queued.

## Build and load

```bash
pnpm install
pnpm --filter @jingle/companion-extension build     # → apps/companion-extension/dist
```

Chrome/Edge → `chrome://extensions` (or `edge://extensions`) → **Developer mode** → **Load unpacked** → select `apps/companion-extension/dist`. Then click the Jingle icon → **Sign in to Jingle**. (Also `docs/office/HUMAN_ACTIONS.md` HA-6.)

Other scripts: `dev` (rebuild on change, then press reload on the extensions page), `test`, `typecheck`, `lint`, `icons` (regenerates `public/icons/*.png` from the gradient + note glyph in `scripts/make-icons.mjs`, mirroring `public/icons/icon.svg`).

## Pairing

1. Popup → **Sign in to Jingle** opens `{origin}/connect/companion?ext=1`.
2. A content script on that page (only on `/connect/companion*` of the configured origin) posts `{type: "JINGLE_COMPANION_READY", version}` to the page, and answers `{type: "JINGLE_COMPANION_PING"}` with READY.
3. The signed-in page issues a scrobble token and calls `window.postMessage({type: "JINGLE_COMPANION_TOKEN", token}, location.origin)`.
4. The extension accepts it only from the same window and same origin, with that exact type; the worker additionally checks the page origin equals the configured Jingle origin, validates with `GET {origin}/ingest/1/validate-token` (expects `{valid: true, user_name}`), stores it, and replies `{type: "JINGLE_COMPANION_PAIRED", ok, userName?, error?}` (`error` ∈ `invalid_token`, `unreachable`, `wrong_origin`, `extension_error`).

Fallback: paste a token under **Paste a token instead** in the popup.

## How to verify

1. `pnpm --filter @jingle/companion-extension test` (connectors against fixtures, scrobble timing with a fake clock, LB payload snapshot, pairing origin checks, queue retry).
2. Load unpacked, sign in, play a song on any of the four players. Within a few seconds Jingle shows you Live; the popup shows "Now: …".
3. Pause: after ~90 s Jingle shows Recent. Play past half the song: the listen appears in your history.
4. DevTools → the extension's service worker → Network: every request goes to your Jingle origin only.

## Layout

```
public/            manifest.json, popup.html/css, icons
src/connectors/    one small file per player + common MediaSession helpers
src/content/       observer (2 s poll + media events, dedupe), per-player entry scripts, pairing
src/background/    scrobbler (pure), payload (LB format), client, queue, service (wiring), index (worker)
src/popup/         popup UI
scripts/           build.mjs (Vite, one bundle per entry), make-icons.mjs
tests/             Vitest + jsdom, fixtures/
```

No code was copied from Web Scrobbler; the implementation is original. Icons are Jingle-original; no platform logos are used.
