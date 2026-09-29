# S2-EXT code review: Jingle Companion MV3 extension

- Reviewer: code-reviewer (independent)
- Branch: `worktree-agent-ab13c693ba244a2f2` (commit 4071af0), diff `main...branch -- apps/companion-extension`
- Checked against: `.claude/agents/extension-engineer.md`, `docs/architecture/CONTRACTS.md`, ADR-0002, ADR-0003, ADR-0014, ADR-0016, `docs/research/listenbrainz.md`, `docs/research/web-scrobbler-and-extension.md`, `docs/PLAN.md` §3.
- No Gherkin exists for this ticket on main (no story file for S2-EXT / JNG-01-14 capture side), so behaviour was checked against the brief and ADRs.

## Summary

The work is solid overall. The scrobble engine is pure and well tested with a fake clock. The payload matches the ListenBrainz `submit-listens` format. Connectors read MediaSession and the page's media element first. Network use is limited to `{origin}/ingest/1/*`. Pairing checks the message source window and origin, and the worker checks the configured origin again. The token is kept in `chrome.storage.local` only and never logged. The icons are Jingle's own. Two issues block approval. One breaks the no-false-Live hard rule. The other contradicts ADR-0016.

## Blocking issues

### B1. Stale sessions heartbeat `playing_now` forever, so Live can be false (PLAN §3 rule 1, BR-01)
- Where: `src/background/scrobbler.ts:102-114` (`tick()`), wired by `src/background/index.ts:41-43` (the 30 s alarm).
- Why: `tick()` treats a session as playing until the content script says otherwise. It sets `s.lastUpdateAt = t` and sends a heartbeat whenever `isPlaying` is true. It never checks when the content script last reported. The content script only sends `null` on `pagehide` (`src/content/run-player.ts:14`). If that never happens, the worker keeps sending `playing_now` every 30 s with no end. Cases where it never happens:
  - the renderer crashes ("Aw, Snap": the tab still exists, so `tabs.onRemoved` does not fire);
  - the page hangs or the tab is frozen;
  - the content script is orphaned;
  - the laptop sleeps mid-song and wakes with the player stopped before the page reports.

  In each case Jingle shows the user Live for a song they are not playing, which breaks rule 1. The same path also credits play time, so it sends a `single` for a listen that never happened.
- Reproduced: in a scratch Vitest file, one `update(playing)` followed by 60 `tick()` calls 30 s apart, with no content updates, produced **60 `playing_now` and 1 `single`** over 30 minutes.
- Fix: add a staleness rule in the scrobbler, for example `RULES.staleMs = 45_000`. The observer keepalive is 15 s, so 45 s means three missed keepalives. In `tick()`, when `t - lastContentUpdateAt > staleMs`:
  - end the session, or mark it not playing;
  - send no heartbeat;
  - credit no play time past the last real update.

  Keep a separate `lastContentAt` field, because `lastUpdateAt` is overwritten by `tick()` today. Add a test: "no heartbeat and no single after the content script goes silent". The existing test "heartbeats playing_now every 30 s while playing" (`tests/scrobbler.test.ts:46`) ticks with no content updates. It has to feed updates, or it will encode the bug.

### B2. Default Jingle origin is `http://localhost:8080`, but ADR-0016 makes it `http://127.0.0.1:8080`
- Where: `src/shared/settings.ts:3` (`DEFAULT_ORIGIN`), `public/popup.html:52` (placeholder), `README.md:20`, `src/popup/popup.ts:17` (error copy "or http://localhost").
- Why: ADR-0016 §6 and `.env.example` set `PUBLIC_BASE_URL=http://127.0.0.1:8080` so that Jingle's cookies share one origin. The user's session therefore lives on 127.0.0.1. "Sign in to Jingle" opens `http://localhost:8080/connect/companion?ext=1`, where the user is signed out. Any absolute redirect built from `PUBLIC_BASE_URL` then lands on 127.0.0.1. `Companion.pair` compares the page origin exactly with the configured origin (`service.ts:145`), so it returns `wrong_origin` and the main pairing path fails out of the box.

  The manifest already covers both hosts (`host_permissions` and the pairing `matches`). That part is correct; only the default is wrong.
- Fix: set `DEFAULT_ORIGIN = "http://127.0.0.1:8080"`, keep `localhost:8080` in `BUILTIN_ORIGINS` as the alternative, and update the placeholder, the README and the tests that assume localhost. The exact-match origin check in `pair` is right; keep it. Separately, CONTRACTS.md §1 still says the edge is `http://localhost:8080`. The orchestrator should bring that in line with ADR-0016.

## Non-blocking suggestions

1. **Pairing contract is undocumented.** The `window.postMessage` protocol (`JINGLE_COMPANION_PING/READY/TOKEN/PAIRED`) and the `/connect/companion?ext=1` page are a new contract between the web app and the extension. It is described only in the extension README. Add it to `docs/architecture/CONTRACTS.md` so the web team builds against the same shapes.
2. **`music_service` value.** `src/shared/types.ts:24-29` sends the player host (`open.spotify.com`, `music.amazon.com`). The research doc defines `music_service` as the service's canonical domain (e.g. `spotify.com`). Ingest maps both, so this is harmless. Sending canonical domains (`spotify.com`, `music.apple.com`, `music.youtube.com`, `amazon.com` or `music.amazon.com`) would match ListenBrainz better if relaying is ever turned on.
3. **Custom loopback ports cannot be granted.** `normaliseOrigin` accepts `http://localhost:<any port>`, but `optional_host_permissions` lists only `https://*/*`. So `chrome.permissions.request` for, say, `http://localhost:3000/*` throws, and `applyOrigin` in `popup.ts:80-86` does not handle the rejection. Either reject loopback ports other than 8080, or add `http://localhost/*` and `http://127.0.0.1/*` to the optional host permissions and catch the rejection.
4. **Permissions can be tighter.** `host_permissions` for the four player hosts and the Amazon regional hosts are not needed. `content_scripts.matches` already allows injection, and the worker never fetches those hosts. The brief allows them, but dropping them shrinks the install warning and follows "minimal permissions". `optional_host_permissions: ["https://*/*"]` is acceptable because it is only requested for one origin at a time. Mention it in the README anyway.
5. **Turning off one platform should end its session at once.** `updateSettings` calls `endAll()` for Pause but not for a platform toggle. The session keeps running until the next content keepalive (up to 15 s), and in that window one more heartbeat can go out. End sessions whose `track.platform` was just disabled.
6. **A failed `playing_now` is not retried** until the next heartbeat. With the tick fired after every 15 s keepalive, the gap stays under about 60 s, so the 90 s Live window holds. Two failures in a row would still let Live lapse. A retry on the next tick would be cheap.
7. **bfcache restore.** `pagehide` stops the observer, but nothing restarts it on `pageshow` with `persisted = true`. The player pages are single-page apps, so this is rare. It is a one-line fix.
8. **Queue cap test** takes about 4.4 s (500 `structuredClone` writes). It could build the array once to keep the suite fast.

## Checks against the brief and hard rules

- ListenBrainz payload: `listen_type` is `single` or `playing_now`, with exactly one listen. `single` carries integer `listened_at` (the start time, in seconds); `playing_now` has none. `artist_name` and `track_name` are required; `release_name` is optional. `additional_info` carries `duration_ms` (never `duration` as well), `origin_url`, `submission_client`, `submission_client_version` and `music_service`. Header `Authorization: Token <t>`, sent to `{origin}/ingest/1/submit-listens` with `credentials: "omit"`. Validation uses `GET /ingest/1/validate-token` and reads `valid` and `user_name`. Correct.
- Thresholds: `min(duration/2, 4 min)`, tracks shorter than 30 s never scrobble, and unknown duration waits 4 min. Played time is wall-clock time while playing, so seeking forward is not counted. Tested. Correct.
- Heartbeat: sent on start and on resume, then every 30 s or more. It comes from the alarm (`periodInMinutes: 0.5`) and from a tick after each content keepalive (15 s), and stops when paused. This meets ADR-0014, apart from B1.
- Connectors: MediaSession metadata and the page's media element come first. DOM selectors are used only as fallbacks (YouTube Music title and byline, Spotify clock labels and track link). No platform endpoints are called, and no cookies or other users' data are read. Correct.
- Network: the only `fetch` is in `client.ts`, and it goes to the configured origin (checked in the source and in `dist/background.js`). Artwork URLs are neither fetched nor sent. Correct.
- Pairing origin checks: the content script checks `ev.source === window && ev.origin === location.origin`, the exact message type and that the token looks plausible. The worker checks that the sender is its own extension, that the message came from a tab, and that the tab origin equals the configured origin. Popup-only messages from tabs are rejected. Correct.
- Token: stored only in `chrome.storage.local`, entered in a password field, and never logged (no `console.*` anywhere in `src`). It is removed on sign-out and on origin change. Correct.
- Brand safety: the icon is Jingle's own (gradient and note glyph), and platform names appear as text only. No Web Scrobbler code was copied, so no `THIRD_PARTY_NOTICES` file is needed. Correct.
- Spotify isolation: the extension never touches the Spotify API. Its events are `COMPANION` (trainable per ADR-0007 and the research doc). Correct.
- Route words: they appear only in the extension's own UI, which is the connection surface. Acceptable under ADR-0002 and the UX spec.

## Tests run and result (in the worktree)

- `pnpm --filter @jingle/companion-extension test`: 7 files, **63 passed**, 0 failed (10.4 s).
- `pnpm --filter @jingle/companion-extension typecheck`: clean.
- `pnpm --filter @jingle/companion-extension build`: `Built Jingle Companion 0.1.0 → dist/ (7 bundles)`. `dist/` holds the manifest, background.js, popup, icons and 5 content scripts, and it is git-ignored.
- Extra reviewer check (scratch file, not committed): a stale-session simulation confirmed B1 (60 heartbeats and 1 false single over 30 min with no content updates).

The tests assert behaviour, not just that code runs: payloads are compared exactly, thresholds are checked with a fake clock, and origin rejection cases are covered. The one gap is the missing staleness test (B1).

VERDICT: CHANGES REQUESTED
