# Code review: S1-INGEST (JNG-01-13 push endpoint, identity resolver v1, adapter base)

- Branch: `worktree-agent-a18fd9124d42d852b` (commit 7581799), reviewed as `git diff main...branch`
- Reviewer: code-reviewer (independent)
- Read against: story JNG-01-13 + branch feature file, CONTRACTS §2/§4/§5/§6, ADR-0003/0006/0007/0013/0014/0016, `docs/research/listenbrainz.md`, `jingle-source-adapter` skill, `services/core_api/sources/models.py`, PLAN §3.

Overall this is careful work. The wire format, auth, BR-01 handling, the SQLAlchemy mirror and the resolver are mostly right, and the tests check real behaviour. Three things need fixing before merge.

## Blocking issues

### B1. A resent listen is stored twice (no idempotency)
`services/ingest_ml/ingest_ml/push/service.py:332-345` (Mongo `insert_many`), and the write order at `:345-357`.

I tested it: posting the same `single` twice gives 2 documents in `listens`. This is not a rare case:
- Scrobblers (Web Scrobbler, and our own Companion queue) retry when a request times out or gets a non-200 response.
- The write order makes retries likely to duplicate. Mongo is written first, then `last:`, the stream, and finally the Postgres upsert. If Postgres fails, the client gets a 500 after the listen is already stored, and its retry stores it again.

`listens` feeds stats, compatibility, recaps, Blends and training, so duplicates skew every metric for good. ListenBrainz itself dedupes on (user, listened_at, track).

Cheapest fix (about 15 lines):
- Compute `dedupe:{user_id}:{listened_at}:{sha1(norm_key)}` for each `single` or `import` listen, using `normalise()` before resolution so duplicates skip the resolver as well.
- Pipeline `SET key 1 NX EX 86400` for each one and drop listens whose SET failed.
- If the Mongo insert fails, `DEL` the keys you just set so the retry can succeed. If you prefer, set the keys only after a successful insert.
- Also make `event_id` deterministic: `uuid5(NS, f"{user}|{listened_at}|{norm_key}")`. Downstream consumers of `events:listen` can then dedupe as well.
- Add a test that a resent `single` leaves exactly 1 document and 1 stream entry.

A 24 h window does not catch re-imports of old history. Record that as a known limit, or for `import` also query `listens` for `{meta.user_id, played_at in batch}` before inserting.

### B2. `validate-token` returns the internal user UUID as `user_name`
`services/ingest_ml/ingest_ml/api/push.py:401-408`; test `tests/test_push_api.py:28-36`.

- The research doc (`docs/research/listenbrainz.md` Impact 3) says to return the Jingle username, not an email or UUID.
- The Companion reads `user_name` for "Connected as @…" (see `docs/office/reviews/S2-EXT-code.md:51`). Web Scrobbler shows it too.
- With this code, users see a raw UUID, and we hand our internal primary key to third-party clients.

The username is available. `users` is Django's `AbstractUser`, so it has a `username` column, and ingest-ml already mirrors `users` in `db.py:48`. Reading it is allowed; ADR-0006 limits only writes.

Fix:
- Add `Column("username", String(150))` to the `users` mirror.
- Join it in `lookup_token` (or run a second select when `validate-token` is called) and return it.
- Update the test to assert the username.

### B3. Mongo `listens` documents drop the lineage flags that the merge target requires
`services/ingest_ml/ingest_ml/push/service.py:332-344`, and `ListenEvent(...)` at `:312-319`.

- On `main`, CONTRACTS §5 and ADR-0013 add `analytics_allowed`, and `permitted_for_analytics()` gates stats, Blends and similar features on it.
- The branch builds the Mongo document by hand. It keeps `trainable` but leaves out `analytics_allowed`, `played_at_estimated`, `artwork_url` and `kind`.
- For COMPANION the value would be `true`, but this function is the pattern the DIRECT-Spotify adapter will copy. A stored listen without the flag breaks the gate that enforces Spotify Policy III.13 (PLAN §3 rule 3).

Fix after rebasing on `main`:
- Set `analytics_allowed=default_analytics_allowed(via, platform)` explicitly on the `ListenEvent`.
- Build the document from `ev.model_dump()`: `user_id`, `platform` and `via` go into `meta`, and every flag stays top-level.
- Assert `analytics_allowed` and `trainable` in `test_listen_inserts_mongo_and_last_only_if_newer`.

## Evaluation of the author's declared deviations

| Deviation | Verdict |
| --- | --- |
| `last:` `observed_at` = min(played_at, received_at) for LISTEN | **Acceptable.** It is more honest for Recent than receive time, it is clamped so it is never in the future, and Live is untouched because only `np:` is read for Live. But the hash field `observed_at` now differs from the `observed_at` inside the embedded `event` JSON, and CONTRACTS §6 says `last:` has "same fields as np". Document this in §6 (with an ADR line) before S4 reads it (non-blocking N2). |
| `validate-token` `user_name` = UUID | **Not acceptable**, see B2. |
| Duplicates not deduplicated | **Not acceptable**, see B1. |
| Rate limit per valid token only | **Acceptable for the pilot.** Brute force is infeasible (`jng_` plus 256-bit token). The remaining risk is DoS: each bad-token request costs a Postgres transaction. See N3. |
| `import` resolves locally only | **Acceptable.** It avoids 1000 MusicBrainz calls at 1 req/s. Listens stay `unresolved` and are queued (see N7). |

## Other checks (pass)

- **BR-01 / no false Live.** `np:` is written with HSET+EXPIRE in one MULTI, TTL = `LIVE_MAX_AGE_SECONDS` (90 s), `observed_at` is server receive time, and only `playing_now` writes `np:`. `NowPlaying.from_adapter` asserts `caps.live`. The acceptance test checks TTL ≤ 90 and observed_at within 2 s.
- **Route words.** `via` appears only in Redis/stream/Mongo `meta`, never in HTTP responses or error text. Errors use ListenBrainz text only.
- **Trainable.** `default_trainable(COMPANION, *)` = true. This matches ADR-0007: Spotify plays captured by the extension are not API data.
- **MusicBrainz.** Disabled when `MUSICBRAINZ_CONTACT` is empty, and also in demo mode and tests. The UA is `Jingle/0.1 ( contact )`. A shared `rl:musicbrainz` bucket enforces 1/s. The call is time-boxed at 1.5 s and runs outside the DB transaction. Lucene special characters are escaped.
- **SQL injection.** Only SQLAlchemy Core expressions are used, plus a single `text("SELECT 1")`. No string-built SQL.
- **Schema vs Django.**
  - Columns, lengths and nullability match `sources/models.py`.
  - `Uuid` maps to native `uuid` on Postgres and to `CHAR(32)` hex on SQLite, the same as Django.
  - `DateTime(timezone=True)` maps to timestamptz.
  - JSONB is used for `meta`.
  - `recording_links` and `artist_tags` use BigAutoField (`DEFAULT_AUTO_FIELD`).
  - Every insert into a TimeStamped table supplies `created_at`/`updated_at`: platform_connections, linked_sources, scrobble_tokens, recordings, artists. Every update sets `updated_at`.
  - ON CONFLICT targets match Django's `UniqueConstraint`s.
- **Error shapes.** 400/401/429 use `{"code","error"}`, `validate-token` returns the verified shapes, and rate-limit headers match ListenBrainz and include `Retry-After`.
- **Platform order.** Follows ADR-0014: `origin_url` host, then `music_service`, then `music_service_name`.
- **Tokens.** Only SHA-256 is stored, the plaintext is returned once, the access log records method, path and status only, and a test asserts tokens are never logged.

## Non-blocking suggestions

1. **`youtube.com` maps to YOUTUBE_MUSIC** (`push/platform.py:391`, `:405`; asserted in `tests/test_platform_inference.py:24-25`). Web Scrobbler's YouTube connector on `www.youtube.com` will show "Live on YouTube Music" and create a YOUTUBE_MUSIC connection for someone who never used YouTube Music. Consider mapping only `music.youtube.com` and the name "youtube music", with everything else UNKNOWN. This is a product call; flag it to the PM.
2. **Document the `last:` hash semantics** in CONTRACTS §6: for LISTEN, `observed_at` = played_at clamped to receive time.
3. **Rate-limit auth failures.** Add a per-IP bucket (`rl:push:ip:{ip}`, using the trusted `X-Forwarded-For` from Caddy) or a Caddy `rate_limit` on `/ingest/1/*`. `validate-token` is also unmetered.
4. **Throttle the token touch.** `auth.py:261-267` updates `last_used_at` on every request, which means one Postgres write per 30 s heartbeat per user. Update only if the stored value is more than 5 min old.
5. **`listened_at` has no upper bound** (`push/schemas.py:90`). Confirmed: `listened_at: 10**12` raises an unhandled `OSError` in `datetime.fromtimestamp` (`service.py:176`), so the client gets a 500 in a non-ListenBrainz shape. Add `ge=1033430400, le=4102444800` as ListenBrainz does, and add a catch-all handler for `/ingest/1/*` that returns `{"code":500,"error":…}`.
6. **Payload size.** `push.py:333-336` buffers the full body before checking its size. Reject early on `Content-Length`. The per-listen 10,240-byte limit is also not enforced.
7. **Unconsumed queue.** `resolve:pending` (`identity/resolver.py:307-310`) has no consumer yet, grows without bound (up to 1000 entries per import when MusicBrainz is on), and is not listed in CONTRACTS §6. Add it to §6, dedupe on recording_id (use a SET or check before pushing), and cap the length.
8. **Race on `norm_key`.** `norm_key` has no unique index, so concurrent first plays of the same unresolved track create duplicate `recordings` rows (`resolver.py:147`, `:180`). Handle this in the later resolver worker (merge by norm_key) or with a Redis lock per norm_key.
9. **Import cost.** An import makes about 2–3 transactions per listen (resolve, then `_store_links`), so a 1000-listen import is thousands of round trips inside a single request. Batch the local lookups by norm_key/isrc.
10. **`_update_last_if_newer` is not atomic** (`service.py:265-277`, HGET then HSET). Concurrent np and import requests can regress `last:`. Use a small Lua compare-and-set.
11. **All pushes are labelled COMPANION.** Third-party scrobblers pushing to `/ingest/1/*` are recorded as `via=COMPANION`. That is fine for the Live and trainable rules, but keep `submission_client` somewhere (for example in the Mongo `meta` or `provider_payloads`) for lineage, and note it in CONTRACTS §4.
12. **No Postgres test.** Every test runs on SQLite, so nothing checks that the mirror matches Django's migrations. Add a CI job against Postgres after `manage.py migrate` (or a reflection test that compares columns).
13. **Default `SERVICE_TOKEN`.** `settings.py:333` (pre-existing, and the same in core-api) defaults to `test-service-token`, and this branch puts real `/internal/*` routes behind it. Fail closed when `JINGLE_ENV` is not `local` or `test`.
14. **Wrong ADR citation.** The `infer_platform` docstring cites ADR-0013 but the order comes from ADR-0014. `_upsert_sources` cites "ADR-0013..0016", but the rule is in ADR-0014.
15. **Discarded check.** `service.py:309-311` builds `NowPlaying` and throws the result away. The guard is fine, but add a comment that it is a guard, or use the object.

## Tests run and result

In the worktree `services/ingest_ml`:
- `uv sync`: OK
- `uv run ruff check .`: All checks passed
- `uv run mypy ingest_ml`: no issues in 23 source files
- `uv run pytest -q`: **121 passed**, including the pytest-bdd acceptance scenarios for JNG-01-13.

Extra probe (temporary test, removed afterwards):
- Posting the same `single` twice gives 2 `listens` documents (B1).
- `import` with `listened_at: 10**12` raises an unhandled `OSError`, so the client gets a 500 (N5).

The tests check behaviour, not just that code runs: they cover np TTL and observed_at, 401 with no writes, 429 with headers, the `last:` newer-only rule, the DISABLED connection staying disabled, and unsafe URLs being rejected. Missing tests: duplicate resend, a Postgres run, and `analytics_allowed` on stored documents.

VERDICT: CHANGES REQUESTED

## Orchestrator verification of fixes (2026-09-29)
B1 dedupe (Redis SET NX 24 h + uuid5 event ids; test `test_resent_listen_is_stored_once`) ✅ · B2 real username ✅ · B3 lineage flags from `model_dump` (test `test_listen_doc_carries_lineage_flags`) ✅ · out-of-range `listened_at` → 400 ✅ · www.youtube.com → UNKNOWN ✅. ruff, mypy strict clean; pytest green, coverage 91%.
VERDICT: APPROVED
