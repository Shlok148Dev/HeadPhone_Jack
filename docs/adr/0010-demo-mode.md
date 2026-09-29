# ADR-0010: Demo mode (JINGLE_DEMO=1)

- Status: Accepted
- Date: 2026-09-29

With `JINGLE_DEMO=1`, `docker compose up` seeds a world: a demo login `demo@jingle.local` (password documented in the README; demo only), about 12 fake friends spread across Spotify, Apple Music, YouTube Music and Amazon Music, circles, sends, a battle and a recap.

A `demo-simulator` process posts plays through the **real** push endpoint (`/ingest/1/submit-listens`) with each fake user's scrobble token, so Live states come from the real pipeline and obey BR-01. Fake users whose only route cannot produce Live (for example an Amazon Music phone listener) never go Live, exactly as a real user would not.

Artwork in demo mode uses Cover Art Archive URLs where the seed has a release MBID, and the generative cover pattern otherwise. No grey placeholders.

## Addendum (Sprint 1 implementation)

- Personas live in `packages/py-common/jingle_common/demo.py` (13 including the demo login). `seed_demo` (core-api, run by the API entrypoint when `JINGLE_DEMO=1`) creates them with deterministic scrobble tokens derived from `SERVICE_TOKEN` (`demo_token()`); writing `scrobble_tokens` from core-api is a documented, demo-only exception to ADR-0006.
- The `demo-simulator` service (ingest-ml image) backfills ~14 days of history via `import`, then plays like the Companion: `playing_now` every 30 s while "in the browser", one `single` at the end.
- Honest gaps: Spotify phone plays arrive afterwards as Recent (the demo cannot emulate Spotify's Last.fm link, so no phone Live in demo); phone plays on Apple Music, YouTube Music and Amazon Music are not captured; the phone-only Amazon persona (`vikram`) never has data or Live.
- Artwork: generative covers (no release MBIDs verified yet).
- Friendships between the demo login and personas are seeded in Sprint 3 when the social graph exists.
