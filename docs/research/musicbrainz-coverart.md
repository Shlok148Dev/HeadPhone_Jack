# MusicBrainz and Cover Art Archive

Checked: 2026-09-29. Owner: platform-researcher.

> Verification note: the rate-limit and User-Agent rules were read today on the official Rate Limiting page (**verified**). Search syntax, ISRC lookup, Cover Art Archive URLs and licensing are **inferred** from docs as known up to mid-2026 (stable APIs); re-verify the CAA API page before the resolver ships.

## Question
How does the identity resolver search MusicBrainz, what are the usage rules, and how may Jingle display Cover Art Archive images?

## Impact (contradictions with CONTRACTS / ADRs / .env.example / source docs)

1. **User-Agent needs real contact info.** MusicBrainz requires `Application/version ( contact )` where contact is a URL or email. `.env.example` has `MUSICBRAINZ_USER_AGENT=Jingle/0.1 ( pilot; contact via repo )`, which has neither and risks being blocked. Change the example to e.g. `Jingle/0.1 ( https://github.com/<org>/jingle )` or a contact email set by the human.
2. **Rate limit is 1 req/s per IP across all Jingle processes.** ingest-ml workers and the demo seeder share one outbound IP, so the limiter must be global (Redis bucket `rl:musicbrainz`, CONTRACTS §6), not per process. Over the limit MusicBrainz returns **503** for all requests from the IP.
3. **Spotify fallback for ISRC loss** (see `spotify.md` Impact 1): `GET /ws/2/url?resource=https://open.spotify.com/track/<id>&inc=recording-rels` can map a Spotify track URL to a recording where editors have linked it. Coverage is partial; fuzzy match stays the main path.
4. **Cover art is not CC-licensed.** ADR-0010 uses CAA URLs in demo mode; this is fine for display, but images must not be bundled into the repo or used for ML.

## Findings

### Web service basics (rate limit and User-Agent verified)
- Base `https://musicbrainz.org/ws/2/`; add `fmt=json`. No key for reads.
- **Rate limit:** average **1 request per second** per source IP (plus a global cap for well-known UAs); exceeding → `503 Service Unavailable`. Anonymous/generic User-Agents (e.g. `python-requests`) are throttled harder or blocked.
- **User-Agent** header mandatory: `AppName/version ( https://url or email )`.

### Search recordings
- `GET /ws/2/recording?query=<lucene>&limit=10&fmt=json`.
- Query fields: `recording:"Kesariya" AND artist:"Arijit Singh"`, also `release:`, `isrc:`, `dur:[260000 TO 275000]`, `arid:`, `reid:`, `status:official`, `primarytype:`. Escape Lucene specials (`+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /`).
- Response `recordings[]` with `id` (MBID), `score` (0–100; Jingle threshold 90, SRS 4.4), `title`, `length` (ms), `artist-credit[].name`/`.artist.id`, `releases[]` (`id`, `title`, `status`, `release-group.id`), `isrcs[]` (when present).

### ISRC lookup
- `GET /ws/2/isrc/{isrc}?fmt=json&inc=artist-credits+releases` → `{"isrc":"INS181900123","recordings":[{"id":"...","title":"...","length":...}]}`; 404 if unknown. One ISRC can map to several recordings.

### Lookups
- `GET /ws/2/recording/{mbid}?inc=artist-credits+releases+isrcs+url-rels+tags&fmt=json` (url-rels give streaming links for "Open in my app", where editors added them).
- `GET /ws/2/artist/{mbid}?inc=tags+genres` (for `artist_tags`).

### Cover Art Archive
- `https://coverartarchive.org/release/{release_mbid}/front` (original), `/front-250`, `/front-500`, `/front-1200` (sizes by longest side); same under `/release-group/{rg_mbid}/front-250` (picks the group's chosen cover). `/release/{mbid}` returns JSON listing all images with `thumbnails` (`250`, `500`, `1200`, `small`, `large`).
- Responses are **307 redirects** to `archive.org` storage; `404` when no art. Safe to hot-link the `coverartarchive.org` URL in `artwork_url` (browser follows redirect); no key; CAA requests do not count against the MusicBrainz 1 req/s limit.
- Prefer `release-group` front for canonical `Recording` artwork; fall back to Jingle's generative cover (ADR-0010).

### Licensing
- MusicBrainz **core data: CC0** (public domain). Supplementary data (tags, ratings, annotations): **CC BY-NC-SA 3.0** — tags are used for `artist_tags`; commercial use of supplementary data needs a MetaBrainz licence. Credit MusicBrainz on Settings → Connections / About.
- Cover art: the **images are copyrighted by their owners**; CAA publishes them without a licence grant. Displaying album covers to identify the music is common practice (fair-use/fair-dealing reasoning) but not a licence. Do not modify, redistribute in bulk, or train on them. MetaBrainz asks commercial users to become supporters.

## Constraints for Jingle
- Cache every lookup (recording, ISRC, search) in PostgreSQL `recordings`/`recording_links` so each track is resolved once.
- BR-04: MusicBrainz metadata may be used for training (core CC0); tags are CC BY-NC-SA, so avoid them in commercial models without a licence.

## Sources (to re-verify)
- https://musicbrainz.org/doc/MusicBrainz_API
- https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting
- https://musicbrainz.org/doc/MusicBrainz_API/Search
- https://musicbrainz.org/doc/Indexed_Search_Syntax
- https://musicbrainz.org/doc/About/Data_License
- https://musicbrainz.org/doc/Cover_Art_Archive/API
- https://coverartarchive.org/
- https://metabrainz.org/supporters
