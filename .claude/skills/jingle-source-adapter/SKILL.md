---
name: jingle-source-adapter
description: How to add or change a Jingle music-platform adapter in services/ingest_ml — the SourceAdapter interface, Capabilities, NotSupported, route values, rate-limit buckets, token encryption, fixtures and offline contract tests. Use this whenever you touch anything under services/ingest_ml/ingest_ml/adapters, the Connection Orchestrator, the push endpoint, polling, or identity resolution — and whenever someone mentions Spotify, Last.fm, ListenBrainz, Apple Music, Amazon Music, YouTube Takeout or Google Data Portability integration.
---

# Adding or changing a source adapter

Adapters are the only code allowed to talk to music platforms (Technical Bible 1.1). Keeping every platform behind one interface is what lets the feed, Blends and analytics never branch on platform, and it makes a false Live state a type/test failure instead of a user-visible lie.

## The interface

`services/ingest_ml/ingest_ml/adapters/base.py`:

```python
class Capabilities(BaseModel):
    live: bool; recent: bool; top: bool; playlist_write: bool; trainable: bool

class SourceAdapter(Protocol):
    kind: SourceKind
    caps: Capabilities
    async def link(self, user_id, credential) -> LinkedSource: ...
    async def refresh(self, src) -> LinkedSource: ...
    async def now_playing(self, src) -> NowPlaying | None: ...  # raise NotSupported if not caps.live
    async def recent(self, src, since) -> list[RawListen]: ...
    async def top(self, src, window) -> list[RawTrack]: ...
    async def write_playlist(self, src, pl) -> str: ...
```

Anything the platform can't do raises `NotSupported`. `NowPlaying` can only be constructed through `NowPlaying.from_adapter(adapter, …)`, which asserts `adapter.caps.live`.

## Steps

1. **Research first.** Read or create `docs/research/<platform>.md` (platform-researcher). Official endpoints only; no scraping, no private/unofficial APIs.
2. **Declare capabilities truthfully.** Apple Music, Amazon Music and YouTube export: `live=False`. Direct Spotify and Last.fm: `trainable=False` (Spotify Policy III.14; Last.fm terms).
3. **Flags.** Approval-gated adapters (`APPLE_MUSIC`, `AMAZON_MUSIC`, Google Data Portability) check their flag in the registry; when off, the adapter isn't registered and the orchestrator never offers it.
4. **Credentials.** Encrypt with `jingle_common.crypto.encrypt_token()` (AES-256-GCM envelope) before storing `linked_sources.token_ciphertext`; decrypt only inside ingest-ml. Never log tokens, never put them in exceptions.
5. **HTTP.** Use the shared `httpx.AsyncClient` from `ingest_ml/http.py`; wrap calls with `rate_limited(source_kind)` (Redis token bucket at ≤ 80 % of budget) and `with_retries` (max 3, exponential backoff + jitter, honour `Retry-After`). On 401 → mark `NEEDS_REAUTH`; on 429 → back off, keep cached state.
6. **Normalise** to `RawListen` / `ListenEvent` (CONTRACTS.md §5) with `platform`, `via`, `trainable`, ISRC/MBID when present.
7. **Fixtures.** Record real (or documented-example) responses into `services/ingest_ml/tests/fixtures/<source>/*.json`, with secrets and personal names scrubbed. Tests must run offline with `respx` mocking httpx.
8. **Contract tests** in `tests/contract/test_<source>_contract.py`: parse every fixture, assert capability behaviour (e.g. `now_playing` raises `NotSupported` when `live=False`), assert `trainable`, assert 401/429 handling.
9. **Orchestrator.** If the adapter introduces a route, add it to `orchestrator.py` route priority (ADR-0003) and update CONTRACTS.md + an ADR.
10. Run `uv run ruff check . && uv run mypy ingest_ml && uv run pytest` in `services/ingest_ml`.

## Pitfalls

- A NOW_PLAYING older than 90 s is not Live. The resolver compares `observed_at`, not `played_at`.
- `platform` is the player the user used (from ListenBrainz `additional_info.music_service` or the Companion's page), not the route.
- Don't surface route names in error messages that reach the UI; return codes like `SOURCE_REAUTH_REQUIRED`.
