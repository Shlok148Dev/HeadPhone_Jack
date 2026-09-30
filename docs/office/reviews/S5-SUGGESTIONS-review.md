# S5 Friend suggestions — combined review (Orchestrator: code, security/privacy, ML, design checklists)

- Correctness: formula and caps per Tech Bible §5 (≤ 20 results, ≤ 8 zero-mutual taste twins, MMR diversity, ≤ 3 reasons); Adamic–Adar verified by hand-computed test.
- Safety: blocked, non-discoverable, dismissed (< 90 d), pending/existing friends and adult–minor pairs excluded before scoring and again at read time; Gherkin "Suggestion safety" (3 scenarios) passes; offline eval unsafe pairs = 0.
- Privacy/lineage: private users' reasons never mention artists or listening; taste vectors read only `trainable` listens (tested against Mongo documents incl. DIRECT and LASTFM rows).
- Performance: API reads a Redis cache; compute runs on the ML worker.
- UI: Suggestions tab (grid, add/dismiss optimistic, starter state + taste picker), Home "People you may know" shelf, onboarding taste picker and suggestions; screenshots dark/light × 1440/390; axe clean. Avatar initials fixed ("YD", not "Y(").
- Tests: suggestions 15 (pure pipeline, Gherkin, API, lineage, eval); full suite green; E2E 11 green.
- Known limits: home route JS exactly at the 180 kB budget; contact matching not in the web pilot.

VERDICT: APPROVED
