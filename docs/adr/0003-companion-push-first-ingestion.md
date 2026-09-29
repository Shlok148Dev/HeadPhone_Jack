# ADR-0003: Ingestion is Companion push first, bridges second, direct APIs third

- Status: Accepted
- Date: 2026-09-29

## Context
Technical Bible 7.1 makes a ListenBrainz-compatible push endpoint primary. Kickoff §2 adds the Jingle Companion browser extension (built in this repo, Manifest V3, may learn from MIT-licensed Web Scrobbler) and restricts Spotify routes in the web phase to direct OAuth (≤ 5 allowlisted users), Spotify's built-in Last.fm link, and the extension on the Spotify web player.

## Decision
- ingest-ml exposes `POST /ingest/1/submit-listens`, `POST /ingest/1/playing-now` (convenience alias) and `GET /ingest/1/validate-token`, in the ListenBrainz wire format, authenticated with a per-user Jingle scrobble token.
- A new route value `COMPANION` identifies events from the Jingle Companion. It is live-capable.
- Connection Orchestrator route priority:
  - Spotify: DIRECT (user on allowlist and a slot free) → COMPANION (active on the web player) → LASTFM (Spotify's built-in Last.fm link) → LISTENBRAINZ.
  - YouTube Music, Apple Music, Amazon Music: COMPANION (web players) → LISTENBRAINZ or LASTFM (if the user already scrobbles) → EXPORT (YouTube Takeout) → flagged direct APIs.
- Several routes may be active at once. The orchestrator keeps all of them and the card uses the freshest live-capable signal.
- Relaying scrobbles on to the user's own ListenBrainz or Last.fm account is deferred (not needed for the pilot).
