# S11 Security and privacy review (Orchestrator, acting as security-privacy-reviewer, 2026-10-01)

## Scope
The whole stack at the end of Sprint 10: auth, tokens, every API endpoint, the edge, realtime, the extension pairing, data rights, logs and dependencies.

## Findings and actions

| # | Finding | Severity | Action |
| --- | --- | --- | --- |
| 1 | Django `/admin/` was routed by the edge: password login with no rate limit and no second factor | High | **Fixed**: 404 at the edge (dev + prod Caddyfiles); staff use the in-app console |
| 2 | The edge port bound to all interfaces, so the laptop stack was reachable from the LAN | Medium | **Fixed**: binds `127.0.0.1` by default; `JINGLE_BIND` for servers; prod overlay serves 80/443 with TLS + HSTS |
| 3 | Deleting an account that owned a circle cascaded and **deleted the circle for every member**; the same for hosted sessions and created Blends | High (data integrity / rights) | **Fixed**: hand-over before purge (admin → member), sessions hand over, Blends keep `created_by = NULL`; test `test_deleting_an_owner_hands_shared_spaces_over` |
| 4 | The data export covered only S1 data | Medium (DPDP / JNG-13-04) | **Fixed**: export covers every domain; test `test_export_covers_every_domain` |
| 5 | Refresh rate limit of 30/min per IP would lock out a pilot group behind one campus NAT | Medium (availability) | **Fixed**: `AUTH_REFRESH_RATE` (default 120/m); login stays at 10/m per IP+email |
| 6 | PostCSS advisories (2 high, 2 moderate) via `next` | Low (build-time only, our own CSS) | **Fixed**: `pnpm.overrides.postcss >= 8.5.23`; `pnpm audit --prod` is clean |
| 7 | Refresh rotation raced with in-flight navigation and signed people out (69 refresh 401s in one E2E run) | Medium (availability) | **Fixed**: 30 s rotation grace for refresh-rotated tokens only (never after logout); ADR-0011 addendum; tests for both cases |
| 8 | Python dependencies | — | `pip-audit` clean for core-api and ingest-ml |

## Checked, no change needed
- **Object-level access (IDOR sweep).** Every view that loads an object by id scopes it to the caller (membership, recipient, requester or owner) before acting, and returns 404 rather than 403 so existence isn't confirmed. Reviewed: circles, invites, friend requests, sends and deliveries, Blends, sessions and queue entries, battles and votes, recaps, appeals, reports.
- **Staff surfaces** need `is_staff` and are audited. Suspended accounts can only read their standing, appeal and sign out. Muted accounts can't post new public content.
- **Tokens.**
  - The access JWT lives in memory and the refresh token in an HttpOnly cookie.
  - Refresh tokens rotate and the old one is blacklisted.
  - Platform tokens are encrypted with a KEK id (S1).
  - Scrobble tokens are stored as SHA-256 only. Circle links store only a hash.
- **CSP.** Nonce-based `script-src`, `frame-ancestors 'none'`, `worker-src 'self'` for the push service worker. The service worker only opens same-origin URLs.
- **Realtime.** It carries hints only. Session rooms are joined after a core-api membership and blocks check. Anonymous queue adds never serialise the adder.
- **Logs.** No tokens, passwords or secrets are logged. One info line logs a scrobble token *id*, not the token.
- **BR-03 (Spotify).** Direct-Spotify listens (`analytics_allowed=false`) never enter suggestions, Blends, compatibility, stats, recaps or Played detection, and are deleted on unlink.

## Residual risks (accepted for the pilot)
- No second factor for staff. Mitigation: the staff console is in-app behind normal login rate limits, and every action is audited. Add TOTP before growing past the pilot.
- Real web-push delivery is verified only up to the pywebpush call.

Verdict: **no open critical or high issues. Approved for the pilot.**
