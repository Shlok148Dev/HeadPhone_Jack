# Sprint board

Owner = who builds it. Founder directive: the Orchestrator builds; agents only when necessary. Story IDs from SRS v4.0.

## Sprint 2 — Jingle Connect routes
Goal: every platform connects with one button and the best available route, with honest capabilities and no keys needed in demo mode.

### To do
- S2-01 Connection Orchestrator (route priority per ADR-0003; route health; capability resolver) — JNG-01-14
- S2-02 ListenBrainz adapter (token link, poll playing-now/listens, fixtures, contract tests) — JNG-01-02
- S2-03 Last.fm adapter (web auth, `lastfm_link` consent, recent tracks now-playing, rate budget) — JNG-01-02, JNG-01-05
- S2-04 Direct Spotify adapter (PKCE, allowlist of 5, 403 fallback, `analytics_allowed=false`, 24 h deletion) — JNG-01-04
- S2-05 Celery poll tasks via ingest `/internal/poll/*`; adaptive polling (Tech Bible 2.3); drain schedule
- S2-06 YouTube Takeout import (JSON + HTML, ≤ 50 MB, isolated parse, 24 h delete) — JNG-01-06
- S2-07 Flagged adapters: Apple Music (MusicKit), Amazon Music, Google Data Portability — JNG-01-03, 01-07, 01-08
- S2-08 Unlink one source; re-consent notices — JNG-01-09, JNG-01-11
- S2-09 Connect sheet "Other ways to connect" wired to S2-02…06

### In progress

### Review

### Done
- (Sprint 1) S1-CORE, S1-INGEST, S1-DEMO, S1-WEB, S2-EXT Companion extension — see STATE.md

## Carry-over requirements (from reviews)
- WEB-PAIR ✅ done in S1: `/connect/companion` has first-party-only CSP, `frame-ancestors 'none'`, token minted only on click (authenticated POST, never from URL), consent-gated and revocable.
