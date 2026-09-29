# ADR-0007: Display-only Spotify API data

- Status: Accepted (Technical Bible 1.3; SRS BR-03, C-03)
- Date: 2026-09-29

- Events with `via = DIRECT` and `platform = SPOTIFY` carry `trainable = false` and are excluded from every ML job by one lineage helper, `permitted_for_training()`, which has its own unit test.
- Such data is shown only to the user and their friends, with `attribution = "SPOTIFY"` and a link back to Spotify.
- On unlink, a Celery task deletes direct-Spotify events, payloads and tokens at once; an hourly sweeper is the backstop for the 24-hour rule. A test asserts deletion.
- Spotify plays captured by the Companion extension or by Last.fm are **not** Spotify API data. They follow Companion and Last.fm rules (Last.fm events are also `trainable = false` under BR-04).
