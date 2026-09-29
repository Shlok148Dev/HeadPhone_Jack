# YouTube Music history: Google Takeout and the Data Portability API

Checked: 2026-09-29. Owner: platform-researcher.

> Verification note: Data Portability eligibility (EEA + UK), the under-18 exclusion and the restricted-scope security assessment were checked today (official overview page plus DTI/DMA sources: **verified**). The Takeout JSON field layout and API endpoint details are **inferred** from exports and docs as known up to mid-2026; test with a real export before the importer ships.

## Question
What does a YouTube / YouTube Music watch-history export look like, how do we pick out YouTube Music plays, and can the Data Portability API be used without Google approval?

## Impact (contradictions with CONTRACTS / ADRs / .env.example / source docs)

1. **Takeout defaults to HTML, not JSON.** In Takeout → YouTube and YouTube Music → "Multiple formats", history defaults to HTML. Onboarding must tell users to switch history to **JSON**, or the importer must also parse `watch-history.html`. SRS 4.3 step 5 assumes JSON.
2. **Data Portability API is EEA + UK only (verified).** It exists because of the EU DMA; Google offers it in the EEA and voluntarily in the UK, with no timeline for other regions. Indian pilot users cannot use it at all, independent of Google verification. The flagged adapter (`google_dataportability_enabled`) is irrelevant for the pilot; Takeout upload is the only YouTube Music history route. SRS 4.3 step 5 and Tech Bible 2.2 should note the region limit. The API also refuses accounts of users under 18 (consistent with Jingle's 18+ gate).
3. **Restricted scope.** `dataportability.myactivity.youtube` is a restricted scope: production use needs OAuth app verification plus a security assessment (verified; annual CASA renewal inferred). Consistent with ADR-0001 (flag `google_dataportability_enabled` off). An unverified app in "Testing" status can be used by up to 100 listed test users, but refresh tokens then expire after 7 days. `GOOGLE_DATAPORTABILITY_CLIENT_ID/SECRET` names in `.env.example` are fine.
4. **Music plays are "watches".** Takeout records YouTube Music plays in the same `watch-history.json`. There is no duration or completion flag, so every entry is a start, not a completed listen. Importer should treat them as LISTEN with `via = EXPORT` and never Live (already the rule).

## Findings (inferred unless marked in Impact)

### Takeout file
- Path inside the archive: `Takeout/YouTube and YouTube Music/history/watch-history.json` (localised folder names vary by account language; search for `watch-history.json`).
- A JSON **array**, newest first. Entry fields:
  - `header`: `"YouTube Music"` or `"YouTube"` (also `"YouTube Kids"`).
  - `title`: `"Watched <video title>"` (localised verb, e.g. Hindi accounts differ). Strip the leading verb using the known prefix list or by removing the first word when `titleUrl` is present.
  - `titleUrl`: `https://music.youtube.com/watch?v=<id>` for YTM entries, `https://www.youtube.com/watch?v=<id>` otherwise. Missing for removed videos.
  - `subtitles`: `[{"name":"Arijit Singh - Topic","url":"https://www.youtube.com/channel/UC..."}]`. Channel name is the artist; strip the `" - Topic"` suffix. Missing for removed videos.
  - `time`: ISO 8601 UTC, e.g. `"2026-09-28T17:41:03.123Z"`.
  - `products`: `["YouTube"]`. `activityControls`: `["YouTube watch history"]`.
  - `details`: `[{"name":"From Google Ads"}]` on ads — **skip**.
- **YouTube Music detection:** `header == "YouTube Music"` OR `titleUrl` host is `music.youtube.com`. Plain `youtube.com` entries can be kept only if the user opts in (music videos watched on YouTube), cleaned of "(Official Video)" etc. (SRS 4.4 step 3).

```json
[{"header":"YouTube Music","title":"Watched Kesariya","titleUrl":"https://music.youtube.com/watch?v=abc123",
  "subtitles":[{"name":"Arijit Singh - Topic","url":"https://www.youtube.com/channel/UCxyz"}],
  "time":"2026-09-28T17:41:03.123Z","products":["YouTube"],"activityControls":["YouTube watch history"]}]
```

### Data Portability API
- OAuth scope: `https://www.googleapis.com/auth/dataportability.myactivity.youtube` (also `…myactivity.youtube_music`? Not confirmed; YouTube Music activity is believed to sit inside the YouTube My Activity resource group).
- Flow: `POST https://dataportability.googleapis.com/v1/portabilityArchive:initiate` with `{"resources":["myactivity.youtube"]}` → `archiveJobId`; poll `GET /v1/archiveJobs/{id}/portabilityArchiveState` until `COMPLETE`, then download the signed `urls[]` (ZIP with the same JSON layout as Takeout).
- Access types: one-time, or **time-based** (user grants repeated access, up to 180 days) for daily re-exports (Tech Bible 2.2 "every 24 h with time-based consent").
- `POST /v1/authorization:reset` revokes and lets the app request fresh consent.

## Constraints for Jingle
- History only; never Live; `platform = YOUTUBE_MUSIC`; trainable (user-owned export).
- Do not use unofficial YouTube Music APIs (kickoff §3): Takeout, Data Portability and the Companion are the only routes.
- Delete the uploaded archive after parsing; keep normalised events only.

## Sources (to re-verify)
- https://support.google.com/accounts/answer/3024190 (Takeout)
- https://takeout.google.com/
- https://developers.google.com/data-portability
- https://developers.google.com/data-portability/user-guide/overview
- https://developers.google.com/data-portability/reference/rest
- https://developers.google.com/data-portability/schema-reference/my_activity
- https://support.google.com/cloud/answer/9110914 (restricted scope verification)
- https://support.google.com/cloud/answer/13463073 (testing mode, 7-day refresh tokens)
- https://developers.google.com/data-portability/policy
- https://dtinit.org/blog/2025/03/03/report-out-portability-in-practice (EEA/UK availability, secondary)
- https://digital-markets-act.ec.europa.eu/developer-portal/end-user-data-portability_en
