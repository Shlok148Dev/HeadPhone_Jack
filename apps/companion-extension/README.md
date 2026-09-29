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

- **Sends only to your Jingle server** (the address in the popup; default `http://127.0.0.1:8080` per ADR-0016, `http://localhost:8080` also accepted). No analytics, no third parties.
- Fields sent (ListenBrainz format, `POST {origin}/ingest/1/submit-listens`, `Authorization: Token <your token>`): artist, track title, album (if known; each capped at 512 characters), and `additional_info` = `music_service` (player host), `origin_url`, `duration_ms`, `submission_client` = "Jingle Companion", `submission_client_version`. Finished listens also carry `listened_at` (start time). Artwork is never sent.
- `origin_url` is a link to the **playing** track only: the YouTube Music `watch?v=` link, the Spotify track link from the player bar, and for Apple Music the song page only when that page is the track that is playing (title and artist match), stripped to address + path (no query string). Browsing other pages is never reported. Amazon Music sends none.
- Nothing is sent while **Pause sharing** is on, for players you switched off, before you sign in, or after Jingle rejects the token (until you sign in again).
- **Stored locally in this browser** (`chrome.storage.local`, unencrypted like all extension storage): your token, your settings, and an offline queue of up to 500 finished listens (artist, title, album, time, link) waiting to be sent. The queue is cleared on sign-out, when you sign in (possibly as someone else) and when you change the server address.
- The token is never logged, never shown back in the popup, and is removed on sign-out or when you change the server address.
- Permissions: `storage`, `alarms`; host access to the four players and `127.0.0.1:8080` / `localhost:8080`. A custom Jingle address (https only) is requested at runtime for that one origin, together with `scripting` so its pairing page can hand over the token. When you switch to another address, the old origin's permission is given back (and `scripting` too when you return to a local address). Extension pages run under an explicit CSP (`script-src 'self'; object-src 'none'; base-uri 'none'`).

## Scrobble rules

- `playing_now` when a track starts or resumes, then every 30 s while playing (keeps Jingle's 90 s Live window fresh). Nothing while paused or after the tab closes, so Jingle naturally falls back to Recent.
- No false Live (BR-01): the player page re-reports every 15 s while playing. If it goes silent for 45 s (tab crashed or frozen, laptop asleep), heartbeats stop, and listening time is only credited up to 20 s after the page's last report.
- One `single` per play once you have **listened** to ≥ 50% of the track or 4 min (whichever is first); never for tracks shorter than 30 s. Seeking forward does not count as listening; replaying a finished track counts again.
- `single` listens that fail (offline, server down) wait in the offline queue (max 500, retry 30 s → 1 h backoff). `playing_now` is never queued. If Jingle rejects the token (401/403), all sending and retries stop until you sign in again.

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

Pairing again (even as another Jingle user) first clears the previous account's offline queue and in-progress play.

Fallback: paste a token under **Paste a token instead** in the popup.

**Requirements on the web page** (`/connect/companion`, owned by the web app). `window.postMessage` is visible to every script running in the page, so the token handover is only as safe as that page:
- a strict CSP with no third-party scripts on this route, and `frame-ancestors 'none'`;
- the token is issued only after an explicit user click, through a CSRF-protected POST; never from a URL parameter or fragment, and never automatically on page load;
- the token is a dedicated, revocable scrobble token with ingest scope only, gated server-side on the user's age check and consent, and revoked on consent withdrawal or account deletion.

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
