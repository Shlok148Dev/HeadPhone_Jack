# ADR-0014: Live rule for push routes; tolerant ListenBrainz wire format

- Status: Accepted
- Date: 2026-09-29
- Source: `docs/research/listenbrainz.md`, `docs/research/web-scrobbler-and-extension.md`

## Decision
- **BR-01 stays literal:** Live requires a `playing_now` signal less than 90 s old. We do **not** extend Live by track duration. The Jingle Companion heartbeats `playing_now` every 30 s while playing, so its users stay Live for the whole song. A third-party scrobbler that sends one `playing_now` per track shows Live for 90 s, then Recent with the true time. That is honest, and the Companion is the recommended path.
- Ingest accepts `duration_ms` or `duration` (seconds). Platform is inferred from the `origin_url` host, then `music_service`, then `music_service_name`, else `UNKNOWN`.
- Web Scrobbler's custom endpoint is the full submit URL (`{origin}/ingest/1/submit-listens`) and it never calls `validate-token`, so a connection becomes `CONNECTED` on its first accepted submission.
- `POST /ingest/1/playing-now` is a Jingle convenience alias, not a ListenBrainz endpoint.
