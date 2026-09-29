# ADR-0017: Jingle Connect implementation choices (Sprint 2)

- Status: Accepted
- Date: 2026-09-30
- Deciders: Orchestrator

## Decisions
1. **Who decides what.** core-api checks consents (`activity_sharing` for any route, `lastfm_link` for Last.fm), the Spotify allowlist (Jingle emails, ADR-0013) and feature flags, then asks ingest-ml's Connection Orchestrator for a plan: `redirect` (platform consent screen), `lastfm_then_spotify`, or `browser` (Companion). The web never picks a route (BR-13).
2. **Spotify route order.** Direct (allowlisted, a Development Mode slot free, keys present) → Spotify's Last.fm link (Last.fm keys present) → browser. Missing keys never produce an error, only the next route (BR-15).
3. **OAuth state** lives in Redis (`oauth:{state}`, 10 min, single use via GETDEL), with the PKCE verifier, so callbacks work across `localhost`/`127.0.0.1` without cookies (ADR-0016).
4. **One write path.** Push, polling and exports all go through `ingest_ml/record.py` (`record_plays`): identity resolution, 24 h de-duplication, lineage flags, BR-01 enforcement by `NowPlaying.from_adapter`.
5. **Direct Spotify isolation.** Polled Spotify API plays write no links or artwork into the shared catalog (`catalog_writes=False`); artwork rides on the event only and cards carry `attribution: "SPOTIFY"`. Unlinking or withdrawing consent purges Mongo listens, `np:`/`last:` and stream entries at once.
6. **Polling cadence** (Technical Bible 7.2, pilot scale): Redis ZSET `poll:next`, Celery beat every 10 s calls `/internal/poll/due`; now-playing every 20 s (Spotify) / 30 s (ListenBrainz) / 60 s (Last.fm), recent plays every 5 min (Apple 10 min), ±20 % jitter, per-source token buckets. Presence-based adaptive polling (poll only while a friend is looking) is deferred to Sprint 4, when presence exists.
7. **Unlink semantics (JNG-01-09).** Routes that belong to the platform are deleted and the platform connection becomes `DISABLED`, so Companion pushes for that platform don't silently re-enable it; pressing Connect again re-enables. Past plays stay (they are the user's history) except direct-Spotify data.
8. **Re-consent (JNG-01-11).** A 401 or a Last.fm private profile marks the route and the platform `NEEDS_REAUTH`; Settings shows "Needs reconnect" with a Reconnect button. The in-app notification arrives with notifications in Sprint 10.
9. **Takeout import** runs in ingest-ml as a background task; the upload is written to a temp file, parsed by content sniffing (JSON or HTML) and deleted in `finally` (NFR-SEC-07). Job status is private to its user.
10. **Apple Music (flagged)** records only items newer than the last seen ids, because the endpoint has no timestamps (ADR-0016).
