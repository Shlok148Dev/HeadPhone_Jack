---
name: gherkin-to-tests
description: Turn SRS Gherkin scenarios (JNG-xx-yy) into automated tests — pytest-bdd for backend, Playwright for the browser — with names and files tied to story IDs and the traceability table updated. Use this whenever you implement or verify a user story, write acceptance tests, or someone mentions Gherkin, acceptance criteria, Given/When/Then, a story ID, or the Definition of Done.
---

# Gherkin → tests

A story is Done only when its Gherkin scenarios run green in CI (SRS 3.4). Tying names to story IDs makes the traceability table (`docs/traceability.md`) mechanical and lets anyone find the test for a requirement with one grep.

## Where scenarios come from

`docs/source/srs-v4.md` §6. Copy the scenario text verbatim into a `.feature` file. If an ADR changes the wording (e.g. ADR-0002 removes "via ListenBrainz" from labels), edit the scenario and add a comment `# amended by ADR-0002`.

## Backend (pytest-bdd)

- Feature file: `services/<svc>/tests/features/<epic>/<story>.feature`, e.g. `tests/features/ep05/JNG-05-01_no_false_live.feature`. Tag the feature `@JNG-05-01`.
- Steps: `services/<svc>/tests/acceptance/test_JNG_05_01.py` with `scenarios("../features/ep05/JNG-05-01_no_false_live.feature")`.
- Step functions use factories and API clients, not raw SQL. Time is controlled with `freezegun`/`time-machine` so "120 seconds old" is exact.
- Scenario test functions are generated as `test_<scenario_name>`; keep scenario names specific ("Stale now-playing"), not "Scenario 1".

## Browser (Playwright)

- `apps/web/e2e/<epic>/JNG-05-01.spec.ts`; `test.describe("JNG-05-01 …")` and one `test()` per scenario with the scenario name.
- Run against the Compose stack in demo mode (`PLAYWRIGHT_BASE_URL=http://localhost:8080`).
- Use role/label locators, never CSS classes. Add `await expectNoA11yViolations(page)` (axe) in every spec.
- Screenshots for design review: `await snap(page, "feed", { themes: ["dark","light"], widths: [1440, 390] })` → `artifacts/screenshots/`.

## Timing assertions

Gherkin thresholds ("within 3 seconds", "p95 within 1 second") become explicit timeouts or measured durations with the number in the assertion message. Load-type thresholds go to k6 (`infra/k6/`) with the story ID in the scenario name.

## After writing

Add/update rows in `docs/traceability.md`: `| JNG-05-01 | Stale now-playing | services/core_api/tests/acceptance/test_JNG_05_01.py::test_stale_nowplaying | core_api/feed/resolver.py | ✅ |`.
