# S1-INGEST security and privacy review

Reviewer: security/privacy reviewer (did not write the code).
Scope: `git diff main...worktree-agent-a18fd9124d42d852b` in `services/ingest_ml`: the public `/ingest/1/*` push API, the `/internal/*` service-token API, scrobble-token minting and validation, the identity resolver (MusicBrainz), and writes to Redis, Mongo and Postgres. `infra/caddy/Caddyfile` and `docker-compose.yml` on main were checked for edge exposure.

Paths below are relative to `services/ingest_ml/ingest_ml/` unless stated otherwise.

## What is done well (verified)

- **Token format:** `jng_` + `secrets.token_urlsafe(32)` gives 256 bits of entropy (auth.py:26-27). Only the SHA-256 hex digest is stored, in the `token_sha256` unique column. The plaintext token is returned once and never logged (internal.py:54-56). Test `test_tokens_never_logged` covers this.
- **Lookup and revocation:** the lookup queries by digest and filters `revoked_at IS NULL`, so revocation takes effect immediately (auth.py:52-64, test `test_revoked_token_rejected`). `last_used_at` is updated on each successful lookup (auth.py:65-71). Brute-forcing a 256-bit token is not feasible. `compare_digest` on the digest is redundant but harmless.
- **Service token:** it is compared with `hmac.compare_digest` (auth.py:80). It is enforced for the whole `/internal` router through `dependencies=` (internal.py:20), and test `test_internal_requires_service_token` covers it. The edge also blocks the path: `@internal path /internal/* -> respond 404` (infra/caddy/Caddyfile:26-27). ingest-ml publishes no host port in docker-compose. Starlette does not route `/ingest/../internal/...` to the internal router, and Caddy cleans the path first anyway.
- **Access logs:** they record only method, path and status (middleware.py:51-57), never headers, bodies or query strings. Error messages repeat the field location and the validation message, not the submitted values.
- **SSRF:** the MusicBrainz host comes from settings only, and the `httpx` client uses `follow_redirects=False` (resources.py:44). Cover Art URLs are built from a parsed UUID (resolver.py:160-161). `origin_url` is never fetched. The Lucene query is escaped (musicbrainz.py:41-43).
- **Mongo injection:** there is none. Documents are built field by field from typed pydantic models, and `user_id` comes from the token principal (service.py:216-229). No user-supplied dict reaches a filter or a document.
- **Limits and time checks:** at most 1000 listens per request, `single` and `playing_now` must contain exactly one listen, and artist, title, release and additional_info strings are capped at 1000 characters (schemas.py). Unknown extra fields are accepted but never stored (only `RawTrack` is stored). `listened_at` must be ≥ 0 and no more than 5 minutes in the future (service.py:59-62). All validation runs before any write.
- **Deletion by `user_id`:** the Postgres tables (`scrobble_tokens`, `platform_connections`, `linked_sources`) use `ON DELETE CASCADE`. Mongo `listens` stores `meta.user_id` with an index. Redis `np:{user_id}` and `last:{user_id}` are keyed per user. The `events:listen` stream is covered by M5.

## Findings

### H1 (High): shared track links accept URLs that browsers send to attacker hosts (phishing, cross-user)
`push/platform.py:34-36`, `push/platform.py:74-88`, `push/service.py:84-104`

`safe_platform_url` checks `urlsplit(url).hostname` and then stores the **raw** string. I confirmed the following in the service venv:

- `https://evil.com\@open.spotify.com/track/abc` is accepted as SPOTIFY. Python takes the host from after the last `@` (`open.spotify.com`). WHATWG browsers treat `\` as `/`, so the link goes to `evil.com`.
- `https://amazon.evil.com/x` is accepted as AMAZON_MUSIC, because `"amazon" in host.split(".")` matches any host that has a label named `amazon`.
- `https://user:pw@open.spotify.com:444/track/x` is accepted (userinfo and a non-default port).

`recording_links` belongs to the **shared** catalog, and `on_conflict_do_update` overwrites `url` (service.py:99-103). So any holder of a scrobble token can replace the "Open in <platform>" link that every other user sees for that recording.

Fix:
1. Use an exact host allowlist per platform, for example:
   - SPOTIFY: `open.spotify.com`
   - APPLE_MUSIC: `music.apple.com`
   - YOUTUBE_MUSIC: `music.youtube.com`, `www.youtube.com`, `youtube.com`, `youtu.be`
   - AMAZON_MUSIC: `music.amazon.<tld>` for a fixed list of TLDs such as `.com`, `.in` and `.co.uk`
2. Reject any URL that contains `\`, userinfo (`parts.username`/`password`), an explicit port, control characters or whitespace.
3. Store a **rebuilt** URL, `urlunsplit(("https", host, path, query, ""))`, not the input string. Better still, store only the extracted `external_id` and build the canonical URL on the server (as `spotify_url` already does for bare IDs).
4. Do not let a push overwrite an existing link. Use `on_conflict_do_nothing`, or overwrite only rows where `is_search = true`.
5. Add forbidden-case tests for the three URLs above.

### M1 (Medium): no per-IP limit before token lookup; each bad token costs a Postgres round trip
`api/push.py:43-49`, `api/push.py:113-123`

The token bucket is keyed by `token_id`, so it only applies after a successful DB lookup. Invalid tokens on `submit-listens`, `playing-now` and especially `validate-token` (which returns 200 with `valid:false`, making it a free oracle) are not limited at all. Brute force is not realistic at 256 bits. However, this is an unauthenticated amplification path into Postgres through PgBouncer (NFR-SEC-04), and the edge does not limit it either.

Fix before the pilot:
- Add a second bucket `rl:push:ip:{client_ip}` of about 30 req/min, charged **only on 401 outcomes**. When it is empty, return 429 before calling `lookup_token`.
- Derive the client IP from Caddy's `X-Forwarded-For`, and trust it only from the Caddy network (`--forwarded-allow-ips`).
- Put the same limit on `validate-token`.
- As belt and braces, drop `parse_token_header` results that do not match `^jng_[A-Za-z0-9_-]{43}$` without touching the DB.
- Add a test: 31 bad-token requests from one IP → 429, and no further DB lookups.

### M2 (Medium): request body read into memory with no streaming cap; the edge has no body limit
`api/push.py:21`, `api/push.py:56-59`; `infra/caddy/Caddyfile:20-23`

`await request.body()` reads the whole body before the 10 MB check. A token holder can therefore send a body of any size and exhaust worker memory. 10 MB is also about 10× more than 1000 capped listens need.

Fix:
- Add `request_body { max_size 2MB }` to the `@ingest` handle in Caddy.
- In the app, reject early when `Content-Length` is greater than the cap. Otherwise read `request.stream()` into a buffer and abort with 413 once it passes `MAX_BODY_BYTES`, which should be lowered to about 2 MB.

### M3 (Medium): rate-limit cost is not weighted by listen count, and one token can use up the global MusicBrainz budget
`api/push.py:49`, `push/schemas.py:12`, `push/service.py:175-190`, `identity/musicbrainz.py:92`

One request costs 1 token regardless of size. That allows 60 req/min × 1000 listens = 60k resolver passes per minute per token. Each pass makes several Postgres queries in sequence plus a link upsert. The limit is also per token rather than per user, so minting more tokens multiplies it, and minting has no cap (internal.py:36-56). For `single` pushes (`allow_remote=True`), one user can hold the shared 1 req/s `rl:musicbrainz` bucket, so resolution fails for everyone else.

Fix:
- Charge the bucket `cost = max(1, ceil(len(payload)/50))`, or add a second bucket for listens per user per hour.
- Key the bucket by `user_id` rather than `token_id`.
- Cap active tokens at 5 per user at mint time.
- Give MusicBrainz lookups a per-user sub-budget, or allow at most one remote lookup per request.

### M4 (Medium): `resolve:pending` grows without bound
`identity/resolver.py:298-306`, `identity/resolver.py:431-434`

Every unresolved `import` listen, and every lookup that times out or hits the rate limit, is `RPUSH`ed with artist and title. There is no dedupe, cap or TTL, and nothing in this ticket consumes the list. One 1000-listen import of unknown tracks adds 1000 entries, so Redis grows until it evicts keys or runs out of memory.

Fix:
- Deduplicate by `recording_id`: use a set, or `SADD resolve:pending:ids` followed by a conditional push.
- Cap the length with `LTRIM` to about 50k.
- Add a TTL, or ship the worker in the same sprint.

### M5 (Medium): DPDP deletion and withdrawal are not implemented for the stores this ticket writes
`push/service.py:236-239`; `api/internal.py`

- **Stream:** `events:listen` entries include `user_id` together with track and platform data. Trimming uses only an approximate `MAXLEN 100000`, so at pilot volume entries can survive indefinitely. They also cannot be deleted by user without scanning the stream.
- **Deletion path:** there is no internal endpoint or routine that erases a user's data from Mongo `listens`, Redis `np:`/`last:` and the stream. There is also no bulk "revoke all tokens for a user" call for consent withdrawal. Ingest does not check consent or deletion state; it relies entirely on core-api revoking tokens.
- **Shared catalog:** free text a user pushes (artist, title, album) becomes a `recordings` row that no `user_id` points to. Deleting the user cannot remove it, so the text persists. This is acceptable only if the privacy notice says so.

Fix:
- Trim the stream by time: `XADD ... MINID ~ <now-7d>`, or `XTRIM MINID` on a schedule. Document the stream retention.
- Add `DELETE /internal/users/{user_id}/data` (service-token only). It should:
  - revoke all scrobble tokens,
  - run `listens.delete_many({"meta.user_id": ...})`,
  - `DEL np:{id} last:{id}`,
  - remove the user's entries from the stream by scanning with `XRANGE` and calling `XDEL`,
  - be idempotent and have tests.
- Wire it into the core-api deletion job (≤ 30 d) and the withdrawal flow.

### M6 (Medium): known default service token is used when `SERVICE_TOKEN` is unset or empty
`settings.py:5`, `settings.py:12` (the same pattern is at `services/core_api/core_api/settings.py:76`)

`service_token` defaults to the committed string `test-service-token`. Because `env_ignore_empty=True`, even `SERVICE_TOKEN=` (empty) falls back to it. That token authorizes minting a push token for **any** `user_id`. Network isolation (Caddy 404 and no published port) is the only thing standing in the way.

Fix: when `jingle_env` is not in `{local, test}`, fail at startup if the service token equals a known default (`test-service-token` or the `.env.example` value) or is shorter than 32 characters. Apply the same check in core-api.

## Low

- **L1:** a huge `listened_at` (e.g. `10**20`) raises an uncaught `OverflowError` in `datetime.fromtimestamp`, which becomes a 500 (push/service.py:60). Add `le=` of about 4102444800 to the schema, or catch the error and return a 400. Consider also rejecting `single` listens older than the retention window.
- **L2:** `lookup_token` writes `last_used_at` before the rate-limit check, so every rate-limited request still costs a DB write (auth.py:65-71, push.py:46-49). Throttle the touch, for example only when the stored value is more than 60 s old.
- **L3:** `revoke_scrobble_token` takes only `token_id` (internal.py:59-76). Object-level ownership is left entirely to core-api. Require `user_id` in the path or body and match `WHERE id = :tid AND user_id = :uid`, so that a bug in core-api cannot revoke another user's token. Add a forbidden-case test.
- **L4:** `submission_client_version` (and extra fields) are not length-capped (schemas.py:28). They are not persisted today; add the cap so that stays safe.
- **L5:** `_enrich` lets any pusher fill blank `album`, `duration_ms` and `release_mbid` (and therefore artwork) on shared recordings (resolver.py:241-255). This is a catalog-poisoning risk. Consider accepting enrichment only from MusicBrainz or ISRC-verified data.
- **L6:** artist and title are sent to musicbrainz.org (a third-party processor, with no user identifier) and the contact is in the User-Agent. Disclose this in the privacy notice.
- **L7:** `validate-token` returns the internal user UUID as `user_name` (push.py:130). This is acceptable, but note it in CONTRACTS.

## Secrets

`git grep` on the branch found no keys or private keys. `.env.example` contains only placeholders.

VERDICT: CHANGES REQUESTED
