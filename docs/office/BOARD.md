# Sprint board

Owner: Orchestrator (founder directive: no agents unless necessary). Story IDs from SRS v4.0.

## Sprint 5 — Friend suggestions
Goal: up to 20 explained suggestions that never leak private listening or cross hard boundaries.

### To do
- S5-01 Taste vectors (TF-IDF over artists/tags → SVD, permitted data only) and Qdrant upsert (JNG-03-03)
- S5-02 Candidate generation + hard filters + heuristic scoring + diversify + reasons (Tech Bible §5.1–5.2) (JNG-03-01, 03-02)
- S5-03 `GET /suggestions`, `POST /suggestions/{id}/dismiss` (90 days), discoverability (JNG-03-05, 03-06)
- S5-04 Cold start: onboarding genre/artist picker → provisional taste (JNG-03-07); shared-context signals (JNG-03-08)
- S5-05 Celery: nightly + on-new-friendship recompute; Redis `sug:{user}` cache; offline eval (Recall@20, coverage, safety=0)
- S5-06 UI: People you may know (Home shelf + Friends tab) with reasons, Add/Dismiss

### Done
- Sprint 0–4: see STATE.md
