# ADR-0010: Demo mode (JINGLE_DEMO=1)

- Status: Accepted
- Date: 2026-09-29

With `JINGLE_DEMO=1`, `docker compose up` seeds a world: a demo login `demo@jingle.local` (password documented in the README; demo only), about 12 fake friends spread across Spotify, Apple Music, YouTube Music and Amazon Music, circles, sends, a battle and a recap.

A `demo-simulator` process posts plays through the **real** push endpoint (`/ingest/1/submit-listens`) with each fake user's scrobble token, so Live states come from the real pipeline and obey BR-01. Fake users whose only route cannot produce Live (for example an Amazon Music phone listener) never go Live, exactly as a real user would not.

Artwork in demo mode uses Cover Art Archive URLs where the seed has a release MBID, and the generative cover pattern otherwise. No grey placeholders.
