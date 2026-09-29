# ADR-0002: No route words in the product; `via` is server-internal

- Status: Accepted
- Date: 2026-09-29

## Context
SRS 5.5 gives the `freshness_label` example "Live on Apple Music via ListenBrainz" and sends `via` to the client. PRD 5.4 says "Every card names its source and route". SRS BR-14 (added later, and reinforced by kickoff §2 "Jingle Connect") says routes are never shown.

## Decision
- The FeedCard sent to clients has **no `via` field**. Labels read `Live on Spotify`, `20 min ago on Apple Music` and so on (grammar in `docs/architecture/CONTRACTS.md` §7).
- `via` is stored on every event and linked source for data lineage (BR-04) and debugging.
- Required third-party credits (Last.fm "powered by AudioScrobbler", ListenBrainz, Spotify attribution) appear on Settings → Connections. Spotify attribution and link-back also appear on a card, but only when its data came from the direct Spotify API (BR-03), expressed as the field `attribution: "SPOTIFY"`.

## Conflicts resolved
SRS 5.5 and PRD 5.4 vs BR-14 and kickoff §2: BR-14 wins (kickoff > SRS; within the SRS, the binding business rule wins over an example).
