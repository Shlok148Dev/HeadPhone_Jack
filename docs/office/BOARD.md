# Sprint board

Owner: Orchestrator. All sprints S0–S11 are done. The next phase is in STATE.md.

## Sprint 11 — Hardening (Done)
- S11-01 Security review: Django admin closed at the edge, loopback bind, deletion hand-over, full export, NAT-safe refresh limit, dependency audits clean (`docs/office/reviews/S11-SECURITY-review.md`)
- S11-02 Accessibility pass: axe on every route in both themes, keyboard skip link and focus (`e2e/a11y.spec.ts`)
- S11-03 k6: 50-user smoke run (p95 73 ms, 0 errors); 5,000-user and session-storm scripts written
- S11-04 Performance budgets table and tuning record (`docs/runbooks/performance.md`)
- S11-05 Backups + tested restore (run: counts match); data export covers every domain + UI
- S11-06 Runbooks, pilot deployment guide + TLS overlay, README quick start, HUMAN_ACTIONS HA-8/HA-9
- S11-07 Final STATE
