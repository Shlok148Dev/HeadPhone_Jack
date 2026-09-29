# Platform research index

Owner: platform-researcher. Checked: 2026-09-29. Each note has an **Impact** section listing contradictions with `docs/architecture/CONTRACTS.md`, the ADRs or `.env.example`, and marks each finding "verified (official doc)" or "inferred". Notes with many inferred items say so at the top; re-verify those before building the adapter.

| Note | One-line summary |
| --- | --- |
| [spotify.md](spotify.md) | Dev Mode: 5 users, owner Premium, 127.0.0.1 redirect. The Feb 2026 migration removed ISRC (`external_ids`) and `/me` email. Policy III.13 bans *analysis*, not just ML. Attribution needs Spotify's full logo. |
| [lastfm.md](lastfm.md) | `user.getRecentTracks` (limit 200, `nowplaying`), web auth with MD5 `api_sig`, errors 17/29. ToS: non-commercial, 100 MB cap, "powered by AudioScrobbler" button. Spotify link is made on Last.fm's Settings → Applications. |
| [listenbrainz.md](listenbrainz.md) | Exact `submit-listens` / `validate-token` / `playing-now` / `listens` wire format with JSON examples for the `/ingest/1/*` endpoint. Accept `duration` or `duration_ms`. Derive platform from `origin_url`. |
| [web-scrobbler-and-extension.md](web-scrobbler-and-extension.md) | Web Scrobbler is MIT. The custom LB URL is the full submit URL and it never calls validate-token. Connector approach per player. MV3 rules for the Companion (service worker, host_permissions, Load unpacked). |
| [apple-musickit.md](apple-musickit.md) | ES256 developer token plus Music User Token. Recently-played tracks have **no timestamps** and shallow depth. ISRC filter and artwork templates. Flagged off (paid Developer Program). |
| [google-takeout-and-dataportability.md](google-takeout-and-dataportability.md) | `watch-history.json` fields; YouTube Music = `header "YouTube Music"` / `music.youtube.com`. Takeout defaults to HTML. The Data Portability API is **EEA + UK only** and uses a restricted scope. |
| [amazon-music.md](amazon-music.md) | Web API V2 is a closed beta with LWA OAuth plus an `x-api-key`. It has library and playlists only, with no documented recently-played or now-playing. Stays flagged off. |
| [musicbrainz-coverart.md](musicbrainz-coverart.md) | 1 req/s per IP (503 when exceeded) and a User-Agent with real contact info. Covers recording search, ISRC and Spotify-URL lookups. CAA `front-250/500/1200` URLs. Core data is CC0; cover art is not licensed. |
