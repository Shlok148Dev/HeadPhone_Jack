# ADR-0015: YouTube Music history comes from Takeout only in the pilot

- Status: Accepted
- Date: 2026-09-29
- Source: `docs/research/google-takeout-and-dataportability.md`

The Google Data Portability API is available only to users in the EEA and UK, so Indian pilot users cannot use it regardless of verification. The adapter is still built behind `google_dataportability_enabled` (off). YouTube Music history in the pilot comes from a Takeout upload. The importer accepts both `watch-history.json` and the default `watch-history.html` (both user-owned exports), and the upload screen tells users how to choose JSON.
