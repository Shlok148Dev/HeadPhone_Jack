# S9 Understand: review (Orchestrator, 2026-10-01)

**Scope**
- Backend: `services/core_api/insights/*` (compute, views, monthly recalibrate), demo genre tags.
- Web: `lib/insights.ts`, `/u/[username]` (my stats, 12-month timeline, friend compatibility), PersonRow name links to profiles.
- Fix: login rate limit made configurable (`AUTH_LOGIN_RATE`), which was the cause of flaky full-suite E2E sign-ins.

## Checked
- **BR-09.** No score without a breakdown, in both the API and the component.
- **Gherkin.** "Sound comparison unavailable" appears with no audio numbers (pytest-bdd + E2E).
- **Privacy.**
  - Only friends whose activity I may see get a score.
  - Visibility "nobody" gives 404.
  - Direct-Spotify listens excluded from scores and stats, with a note in stats.
  - Profile fields only for friends.
  - Blocked gives 404.
- **Formula.** Tests cover the Jaccard values, the weights with and without genres, the percentile fallback and calibration, and that the recalibration stores numbers only.
- **Stats and timeline.** Minutes, plays, top artists, genres and platforms; the building state with days remaining; 12 distinct months, with a month-boundary-safe test (one was found and fixed).
- **Charts.** Single-series bars (no legend needed) with direct labels, a hover readout and an sr-only table. axe is clean on both profile views.
- **Coverage.** `insights` is at 96% (tasks wrapper excluded).

## Deferred (recorded)
- Timeline overlay with a friend (JNG-08-04, Could) and the circle taste map (JNG-08-05, Could).
- Audio features (Essentia) for the Sound component, a post-pilot task. The card states the gap honestly.

Verdict: **ship**.
