# S2-EXT: Jingle Companion MV3 extension, security and privacy review

Reviewer: security/privacy reviewer (did not write the code)
Branch: `worktree-agent-ab13c693ba244a2f2`, `apps/companion-extension/` (+ `pnpm-lock.yaml`)
Date: 2026-09-29

## Scope and what was checked

- Manifest: permissions, host_permissions, optional permissions, content-script matches, CSP.
- Pairing: `window.postMessage` protocol (`src/content/pairing-listener.ts`, `pairing.ts`) and the worker side (`src/background/index.ts`, `service.ts#pair`).
- Token storage and transmission (`shared/settings.ts`, `background/client.ts`, `service.ts`).
- Data egress: every network call (only `fetch` in `background/index.ts:11`, used by `client.ts` against the configured origin), payload fields (`payload.ts`), connectors (`src/connectors/*`).
- Offline queue (`queue.ts`), popup (`popup.html`, `popup.ts`), build script, devDependencies and lockfile.
- `git grep` for committed secrets on the branch: nothing found. The only hit is the message-type constant `JINGLE_COMPANION_TOKEN`.
- README privacy section compared against the code.

## What is done well

- **Minimal permissions.** The only required permissions are `storage` and `alarms`. Required host access covers the four players, the 12 Amazon regional hosts and `localhost:8080` / `127.0.0.1:8080`. There is no `tabs`, `webRequest`, `history`, `cookies`, `<all_urls>` or `web_accessible_resources`, and no `externally_connectable`.
- **Optional `https://*/*` and `scripting` are gated.** The popup requests them only when the user clicks, and only for the one normalised origin (`popup.ts:80-85`). The worker registers the pairing script only for `${origin}/connect/companion*`, and only when `permissions.contains` confirms the grant (`index.ts:24-35`). Built-in origins never trigger the request. I accept this design, subject to L1 below.
- **Pairing listener checks.** It requires `ev.source === window` and `ev.origin === location.origin`, the exact `type`, and a plausible token shape (8-512 chars, printable ASCII). It only replies to the page's own origin and has a busy guard (`pairing-listener.ts:32-60`). The worker then checks the sender origin, which Chrome attests via `sender.url`, against the configured origin (`index.ts:67-72`, `service.ts:145`), and validates the token server-side before storing it. Forbidden-case tests exist: cross-origin, foreign window/iframe, wrong shape, implausible token, and wrong origin at the worker (`tests/pairing.test.ts:46-78`, `tests/service.test.ts:46`).
- **Popup-only messages are rejected from tabs.** `sender.id` is checked (`index.ts:58`, `78`).
- **Track messages are gated before anything is sent.** A track message is only accepted if the attested tab host maps to a connector of the same platform, sharing is not paused, the platform is enabled and a token exists (`service.ts:71-79`). Tested at `service.test.ts:76`, `84`, `59`.
- **Token handling.** The token lives only in `chrome.storage.local`, is never logged (no `console.*` in `src/`), and is never returned to the popup (`status()` exposes only `userName`). It is sent only as an `Authorization` header to `{configured origin}/ingest/1/*` with `credentials: "omit"`. It is removed on sign-out and on origin change, and the queue is cleared at the same time, so queued plays can never be flushed to a different server.
- **No platform API or private-endpoint calls.** Connectors read only MediaSession, the page's media element and a few DOM labels. `artworkUrl` is read but never sent. This complies with the kickoff hard rule.
- **Popup safety.** The popup uses no inline script and writes all dynamic text with `textContent`. The MV3 default extension CSP (`script-src 'self'`) applies.
- **Supply chain.** There are no runtime dependencies. All six packages are devDependencies (types, TypeScript, Vite, Vitest, jsdom), locked with integrity hashes. Bundles are built unminified from local sources.

## Findings

### Medium

**M1. Re-pairing as a different Jingle user keeps the previous user's queued listens and scrobble state, and flushes them to the new account.**
`src/background/service.ts:142-154`

`pair()` overwrites `auth` and then calls `flushQueue(true)`. Neither the queue nor the scrobbler/`nowPlaying` state is cleared. On a shared browser, if user B signs in on `/connect/companion`, up to 500 of user A's pending listens are posted to B's history, and A's in-progress play can emit a `single` as B. This is a cross-account data disclosure (DPDP purpose limitation). Pairing is also possible from any page load of `/connect/companion` without signing out first.

Fix: in `pair()`, if an `auth` already exists and the validated `userName` differs from it (or always, which is simpler), clear the queue and call `endAll()` + `persist()` before storing the new token, the same way `signOut()` does. Add a test: pair as A → enqueue → pair as B → assert the queue is empty and no submission carries A's listen under B's token.

**M2. The Apple Music `origin_url` is the page the user is viewing, not the track that is playing, and it keeps query parameters.**
`src/connectors/apple-music.ts:16`

`location.href` is used whenever the user happens to be on any `/xx/song/` page. If they browse song X while track Y plays, the listen for Y is stored with X's URL. That sends a piece of browsing activity to the server, which contradicts the "only the user's own now-playing, no browsing history" requirement and the README's "link to the track". The query string (for example `?l=`, `?i=`, campaign params) is also forwarded.

Fix: only emit `origin_url` if the song page's title matches the MediaSession title (or derive it from the now-playing bar link, as the Spotify connector does). Strip `search` and `hash`, keeping `origin + pathname`. Add a fixture test for "viewing a different song page → no origin_url".

**M3. The token handover via `window.postMessage` exposes the token to every script in the page's main world. The protocol's security therefore depends on requirements for the web page, which are not yet documented.**
`src/content/pairing-listener.ts:32-60`, README "Pairing"

Any script running on `{origin}/connect/companion` can read the `JINGLE_COMPANION_TOKEN` message, and can also post its own token. That includes third-party scripts, other extensions' content scripts, and XSS. A posted foreign token would pair the victim's browser to an attacker's account, which would receive the victim's plays. The extension-side checks are correct; the residual risk is on the page. Replay is not a concern, because a replayed token only re-pairs the same token.

Fix: record these as acceptance criteria for the web ticket that builds `/connect/companion`, and link them from the README:
- (a) strict CSP with no third-party scripts on that route, plus `frame-ancestors 'none'`.
- (b) issue the token only after an explicit user click, through a CSRF-protected POST, never from a URL parameter or fragment, and never automatically on page load.
- (c) the token is a dedicated, revocable scrobble token with only the ingest scope.

Optional hardening: switch to `externally_connectable` with `matches` set to the Jingle origin, and have the page call `chrome.runtime.sendMessage(EXT_ID, …)`. Only the extension then receives the token.

### Low

**L1. Custom-origin permissions accumulate.** `src/background/index.ts:24-35`, `src/popup/popup.ts:80-85`. When the origin changes, the old origin's host permission and `scripting` are never revoked. Fix: call `chrome.permissions.remove({origins: [old + "/*"]})` when leaving a custom origin, and remove `scripting` when returning to a built-in origin.

**L2. Dev defaults would ship to users.** `public/manifest.json:44-45,83`, `src/shared/settings.ts:3`. The default origin `http://localhost:8080` plus the static localhost host permissions mean a store build would, by default, send plays and the token over plain HTTP to whatever local process listens on port 8080. Fix: make the default origin and the localhost entries build-time flags; production builds should default to the production `https` origin and omit localhost.

**L3. A rejected token is retried indefinitely.** `src/background/client.ts:23-24`, `service.ts:118-119`. 401/403 is treated as retryable, so a revoked token (for example after DPDP withdrawal or account deletion) keeps posting `playing_now` every 30 s and retrying the queue. Fix: on 401, stop sending until the user re-pairs. Clear `auth` on 401, or treat 401 as non-retryable for `playing_now` and suspend emission while `lastError === "token_rejected"`.

**L4. No length caps on page-supplied metadata.** `src/connectors/common.ts:45-57,112-126`. Artist, title, album and origin_url come from page-controlled MediaSession/DOM with no limits. Fix: truncate each field in `buildState` (for example 512 chars), and confirm that the ingest endpoint enforces its own limits and rate limit (NFR-SEC-04) for companion tokens.

**L5. Loopback origins other than port 8080 are accepted by `normaliseOrigin` but can never be granted.** `src/shared/settings.ts:44-45`. `optional_host_permissions` only covers `https://*/*`, so `permissions.request` fails for, say, `http://localhost:3000`, and so does `[::1]`. This is not a vulnerability, but the error message (`invalid_origin` copy) is misleading. Fix: accept only the built-in loopback origins over http.

**L6. Local listening history at rest.** `src/background/queue.ts`. Up to 500 queued listens (artist, title, album, timestamp, URL) are stored unencrypted in `chrome.storage.local`. This is acceptable for an extension, but the README privacy section should say so. The queue is cleared on sign-out and origin change.

**L7. Explicit CSP.** `public/manifest.json`. The MV3 default is adequate. Declaring `"content_security_policy": {"extension_pages": "script-src 'self'; object-src 'none'; base-uri 'none'"}` locks it against future regressions.

**L8. DPDP dependencies are on the server.** The extension has no consent, 18+ or withdrawal UI itself, which is appropriate. The server must gate issuing companion tokens on (a) the 18+ check and (b) itemised consent for "browser companion ingestion", and must revoke companion tokens on withdrawal or deletion, which also needs L3. Track this in the server-side ingest ticket.

## README privacy statement accuracy

The statement is mostly accurate. The destination, the fields sent, the fact that `artwork` is not sent, the pause/per-player/pre-sign-in behaviour, the token storage and removal rules, and the permission list all match the code. The following need correcting:
- "`origin_url` (link to the track)" is not true for Apple Music (M2).
- It does not mention the locally stored offline queue of listens (L6).
- "requested at runtime for that one origin only" is true per request, but grants from earlier origins are never revoked (L1).
- It should state the web-page requirements on which pairing security depends (M3).

## Summary

No Critical or High findings. Three Medium findings: M1 and M2 are small code fixes in this ticket; M3 is a documented requirement on the web pairing page. Eight Low findings.

VERDICT: CHANGES REQUESTED

---

## Re-review (commit 9f6d7c6)

Date: 2026-09-29. I read the fix diff for `apps/companion-extension/`. `vitest run` passes (7 files, 74 tests) and `tsc --noEmit` is clean.

| Finding | Status | Evidence |
| --- | --- | --- |
| M1 re-pair carries previous account's data | **Fixed** | `service.ts` `pair()` calls `resetAccountState()` (clears queue, `endAll()`, `nowPlaying=null`, persist) after validation and before storing the new token. The forced flush after pairing is removed. Test: "M1: pairing a new token drops the previous account's queue and in-progress play". |
| M2 Apple origin_url = viewed page | **Fixed** | `apple-music.ts` `appleSongUrl()` requires an exact `/xx/song/<slug>/<id>` path and a page title that starts with the playing title and contains the artist. It returns `origin + pathname` only (no query or hash). Tests cover the matching page and "browsing a different song page ... sends no origin_url". |
| M3 postMessage handover depends on web page | **Carried** | The requirements are recorded in `docs/office/BOARD.md` "Carry-over requirements" (WEB-PAIR) and in the README "Requirements on the web page". This is acceptable for this ticket. The WEB-PAIR ticket's security review must verify them. |
| L1 permission accumulation | **Fixed** | `index.ts` `revokeOldOrigin()` removes the old custom origin's host permission. On return to a built-in origin, it also unregisters the pairing script and removes `scripting`. |
| L2 dev defaults in store build | **Accepted for now** | The default is now `http://127.0.0.1:8080` per ADR-0016, and the localhost host permissions remain. This is fine for the current local-only deployment. It must become a build-time flag (https default, no loopback hosts) before any public or store build. Keep it on the release checklist. |
| L3 401 retried forever | **Fixed** | `usableAuth()` returns nothing while `lastError === token_rejected`, so `emit()` and `flushQueue()` send nothing. `emit()` returns on the first 401. Only a successful re-pair clears the flag, and the popup then shows the signed-out state. Test: "a rejected token (401) suspends all sending ...". |
| L4 no length caps | **Fixed** | `buildState` caps text at 512 and URLs at 2048, and bounds durations. The worker now also validates the message itself: `sanitizeTrack()` checks the platform enum, the types, the 512/2048 caps, https-only URLs and numeric range, and `onTrack` takes `unknown`. Test: "rejects malformed track messages at the worker". The server must still enforce its own limits and rate limit. |
| L5 unreachable loopback origins | **Fixed** | `normaliseOrigin` accepts only https or the built-in http origins. `permissions.request` failures are caught. |
| L6 local queue undisclosed | **Fixed** | The README privacy section now describes what is stored locally and when it is cleared. |
| L7 explicit CSP | **Fixed** | `manifest.json` sets `extension_pages: script-src 'self'; object-src 'none'; base-uri 'none'`. |
| L8 server-side DPDP gates | **Carried** | The README web-page requirements include the age check, consent, and revocation on withdrawal or deletion. These belong to the server ingest and WEB-PAIR tickets. |

The other changes in the commit do not raise security issues:
- Sessions that stop reporting now time out (no heartbeat, no credit after 20 s or 45 s), which strengthens BR-01.
- Switching a platform toggle off ends its sessions immediately.
- Observation resumes when a page is restored from the back/forward cache.

The README privacy statement now matches the code. No new findings.

VERDICT: APPROVED
