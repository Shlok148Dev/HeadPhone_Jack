# Sprint board

Owner: Orchestrator (founder directive: no agents unless necessary; advance sprint to sprint through S11). Story IDs from SRS v4.0.

## Sprint 11 — Hardening
Goal: ship a pilot that is safe, accessible, measured and documented, runnable by Shlok from the README alone.

### To do
- S11-01 Security review: auth, tokens, CSP/headers, rate limits, IDOR sweep over every endpoint, secrets in logs, dependency audit (EP-13)
- S11-02 Accessibility pass: axe on every route, keyboard walkthrough, focus order, reduced motion (JNG-13-07)
- S11-03 k6: smoke at 50 users locally (run + results); 5,000-user scripts written and documented (JNG-13-01)
- S11-04 Performance budgets: route JS table, API p95 from the smoke run
- S11-05 Backups + tested restore runbook (JNG-13-03); data export check (JNG-13-04)
- S11-06 Runbooks, pilot deployment guide (one small server), README 5-minute quick start, HUMAN_ACTIONS refresh
- S11-07 Final STATE: complete / behind flags / known gaps / next phase

### Done
- Sprint 0–10: see STATE.md
