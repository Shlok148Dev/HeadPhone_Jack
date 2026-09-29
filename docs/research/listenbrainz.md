# ListenBrainz API: wire format for Jingle's push endpoint

Checked: 2026-09-29. Owner: platform-researcher.

> Verification note: the core API page and the JSON (`additional_info`) page were read today; items marked **verified** come from them. Other details (tag limits, error bodies, `mbid_mapping`, rate-limit header names, licence) are **inferred** from docs/server source as known up to mid-2026; re-verify before contract tests are frozen.

## Question
What exactly does a ListenBrainz client send and expect, so `/ingest/1/*` is drop-in compatible, and what are the read endpoints and data terms?

## Impact (contradictions with CONTRACTS / ADRs / .env.example / source docs)

1. **`POST /ingest/1/playing-now` is not a ListenBrainz endpoint.** Real clients send now-playing as `POST /1/submit-listens` with `listen_type = "playing_now"`. Keep the alias (ADR-0003) as a convenience, but compatibility depends only on `submit-listens` + `validate-token`.
2. **Clients append paths to a base URL.** Custom-instance settings in scrobblers take a base like `https://host/ingest` (some take the full `…/1/submit-listens` URL, see `web-scrobbler-and-extension.md`). The onboarding copy must show the exact string per client.
3. **`validate-token` shape.** Clients check `valid` and `user_name`; returning Jingle's username (not an email or UUID) avoids leaking identifiers.
4. **`music_service` is optional and Web Scrobbler never sends it (verified from its source).** Tech Bible 2.4 derives `platform` from it. Resolution order should be `music_service` (domain) → `music_service_name` → host of `origin_url` → `media_player` → `UNKNOWN`. Mapping: `spotify.com`/`open.spotify.com`→SPOTIFY, `music.apple.com`→APPLE_MUSIC, `music.youtube.com`→YOUTUBE_MUSIC, `music.amazon.*`→AMAZON_MUSIC.
5. **Accept both `duration` (s) and `duration_ms` (verified).** The spec allows either (not both); Web Scrobbler sends `duration` in seconds. The CONTRACTS §5 `raw.duration_ms` must be normalised from either.
6. **Clients send a LISTEN only after half the track or 4 minutes (verified guidance).** So `single` arrives mid-song, after `playing_now`; ingest must not treat a `single` as "playback stopped".
7. **No playing-now TTL in the payload.** ListenBrainz expires playing-now after the track's duration (or a server default when absent). Jingle's 90 s `np:` TTL (CONTRACTS §6) is stricter and fine, but clients re-send playing_now only once per track, so Jingle must keep the card Live using `duration_ms` (Live until `played_at + duration`, capped) or Live will drop after 90 s mid-song. This needs an ADR clarifying BR-01 for push routes.

## Findings

### `POST /1/submit-listens` (limits and listen_type rules verified; rest inferred)
- Verified: max **1000** listens per request, each listen ≤ **10,240 bytes**, whole payload ≤ **10,240,000 bytes**; submit a listen after the user has heard half the track or 4 minutes, whichever is lower.
- Header `Authorization: Token <user token>`; `Content-Type: application/json`.
- Body: `{"listen_type": "single" | "playing_now" | "import", "payload": [ ... ]}`.
  - `single`: exactly one listen, `listened_at` required (UNIX seconds, integer).
  - `playing_now`: exactly one listen, **no** `listened_at`.
  - `import`: many listens (limit **1000** per request), each with `listened_at`.
- Listen: `{"listened_at": int, "track_metadata": {"artist_name": str (required), "track_name": str (required), "release_name": str (optional), "additional_info": {...}}}`.
- Limits: each listen JSON ≤ **10240 bytes**; ≤ 50 tags, each ≤ 64 chars; `listened_at` ≥ 1033430400 (2002-10-01).
- `additional_info` (all optional; field list verified from the JSON doc; `music_service` = "the canonical domain of this service", e.g. `spotify.com`; `music_service_name` only when no domain is known; also `original_submission_client`, `duration_played` (s), `label`): `artist_mbids[]`, `release_group_mbid`, `release_mbid`, `recording_mbid`, `track_mbid`, `work_mbids[]`, `tracknumber`, `isrc`, `spotify_id` (open.spotify.com URL), `tags[]`, `duration_ms` (int) **or** `duration` (int s, not both), `media_player`, `media_player_version`, `submission_client`, `submission_client_version`, `music_service` (canonical domain, e.g. `spotify.com`), `music_service_name` (display name when no domain), `origin_url` (URL where the track was played). Unknown keys are allowed and stored.
- Success: `200 {"status": "ok"}`. Errors: `400 {"code": 400, "error": "..."}`, `401` bad/missing token, `429` rate limited.

```json
{"listen_type":"playing_now","payload":[{"track_metadata":{
  "artist_name":"Arijit Singh","track_name":"Kesariya","release_name":"Brahmastra",
  "additional_info":{"duration_ms":268000,"music_service":"music.youtube.com","music_service_name":"YouTube Music",
    "origin_url":"https://music.youtube.com/watch?v=abc123","media_player":"Chrome",
    "submission_client":"Jingle Companion","submission_client_version":"0.1.0"}}}]}
```

What Web Scrobbler actually sends (verified from its source; no `music_service`, `duration` in seconds):

```json
{"listen_type":"playing_now","payload":[{"track_metadata":{
  "artist_name":"Arijit Singh","track_name":"Kesariya","release_name":"Brahmastra",
  "additional_info":{"submission_client":"Web Scrobbler","submission_client_version":"3.x",
    "music_service_name":"YouTube Music","origin_url":"https://music.youtube.com/watch?v=abc123","duration":268}}}]}
```

```json
{"listen_type":"single","payload":[{"listened_at":1790676902,"track_metadata":{
  "artist_name":"Arijit Singh","track_name":"Kesariya","release_name":"Brahmastra",
  "additional_info":{"recording_mbid":"00000000-0000-0000-0000-000000000000","isrc":"INS181900123",
    "duration_ms":268000,"music_service":"spotify.com","origin_url":"https://open.spotify.com/track/xyz",
    "submission_client":"Jingle Companion","submission_client_version":"0.1.0"}}}]}
```

### `GET /1/validate-token` (response shape verified; `user_name` omitted when invalid)
- Token in `Authorization: Token <t>` (legacy `?token=` also accepted).
```json
{"code":200,"message":"Token valid.","valid":true,"user_name":"aanya"}
```
```json
{"code":200,"message":"Token invalid.","valid":false}
```

### `GET /1/user/{user_name}/playing-now` (verified: same format as `/listens`, at most one listen, no `listened_at`)
```json
{"payload":{"count":1,"user_id":"aanya","playing_now":true,
  "listens":[{"playing_now":true,"track_metadata":{"artist_name":"Arijit Singh","track_name":"Kesariya",
    "release_name":"Brahmastra","additional_info":{"music_service":"spotify.com"}}}]}}
```
Empty: `count: 0`, `listens: []`. No `listened_at` and no observed timestamp: Jingle sets `observed_at` = poll time.

### `GET /1/user/{user_name}/listens?min_ts|max_ts&count`
- `count` default 25, max **1000** (max verified); `min_ts`/`max_ts` UNIX s (not both).
```json
{"payload":{"count":1,"user_id":"aanya","latest_listen_ts":1790676902,"oldest_listen_ts":1600000000,
  "listens":[{"listened_at":1790676902,"inserted_at":1790676905,"recording_msid":"uuid","user_name":"aanya",
    "track_metadata":{"artist_name":"Arijit Singh","track_name":"Kesariya","release_name":"Brahmastra",
      "additional_info":{},"mbid_mapping":{"recording_mbid":"uuid","artist_mbids":["uuid"],"release_mbid":"uuid"}}}]}}
```
`mbid_mapping` (server-side MusicBrainz mapping) is present when LB has resolved the listen; use it before fuzzy matching.

### Rate limiting
- Headers on every response: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset-In` (seconds), `X-RateLimit-Reset` (epoch s). Over limit → `429`. Limits are per token (or per IP when anonymous). Jingle's own endpoint should emit the same headers so clients back off correctly.

### Licence and attribution
- Listen data is published by MetaBrainz under **CC0** (public dumps). No legal attribution requirement, but MetaBrainz asks for credit and, for commercial use, a MetaBrainz supporter tier. Jingle credits ListenBrainz on Settings → Connections (ADR-0002). BR-04 permits training on it.

## Constraints for Jingle
- Store only the SHA-256 of Jingle scrobble tokens (CONTRACTS §3); a user's own ListenBrainz token (poll route) is stored encrypted.
- Poll `playing-now` at 30 s only when viewed and not pushing; stay under 80% of `X-RateLimit-Limit`.

## Sources (to re-verify)
- https://listenbrainz.readthedocs.io/en/latest/users/api/core.html
- https://listenbrainz.readthedocs.io/en/latest/users/json.html
- https://listenbrainz.readthedocs.io/en/latest/users/api/index.html (rate limiting)
- https://github.com/metabrainz/listenbrainz-server/blob/master/listenbrainz/webserver/views/api_tools.py
- https://metabrainz.org/datasets and https://listenbrainz.org/data/
