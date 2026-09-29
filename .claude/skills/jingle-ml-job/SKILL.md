---
name: jingle-ml-job
description: How to add or change a Celery ML job in Jingle (taste vectors, friend suggestions, suggested circles, compatibility, Blends, recaps, explanations) — permitted-data lineage (trainable), deterministic scoring per the Technical Bible, idempotency, evaluation metrics, and MLflow/JSON run logging. Use this whenever you write or modify anything in services/core_api/jingle_ml, any scoring/ranking/clustering code, or any job that reads listens to compute something about users.
---

# Adding an ML job

Jingle's models decide who to suggest, what goes in a Blend and what a score means, so they must be explainable, reproducible and legal. The legal part is concrete: Spotify API data and Last.fm data may not train models (BR-03, BR-04, Spotify Policy III.14).

## Steps

1. **Spec**: find the formula in `docs/source/technical-bible.md` §5–6 and implement it exactly (weights, thresholds, caps). If you must deviate, write an ADR.
2. **Data access**: read listens only through `jingle_ml.data.load_listens(user_ids, window, purpose=...)`. `purpose="train"` applies `permitted_for_training()` (drops `trainable=False`); `purpose="display"` may include all sources the user can see. Never bypass it — there is a unit test that every job calls it.
3. **Hard filters before scoring** (suggestions): existing friends, pending requests, blocks either way, discoverability off, dismissed < 90 days, suspended, adult–minor. Test each one.
4. **Explanations**: build reasons from a facts dict; ≤ 3 reasons; template first; no data from users in Private mode; optional LLM rephrase must validate against facts or fall back.
5. **Job**: Celery task in `jingle_ml/tasks.py` on queue `ml`, idempotent key `(job, entity, period)`, max 3 retries with jitter. Results cached (e.g. Redis `sug:{user_id}` 24 h) and/or written to PostgreSQL through core-api models.
6. **Evaluation**: add an offline eval in `jingle_ml/eval/` producing the Technical Bible metrics (Recall@20, coverage, safety=0). Log params/metrics with `jingle_ml.tracking.log_run()` (MLflow if `MLFLOW_TRACKING_URI` set, else `artifacts/ml/<job>/<timestamp>.json`).
7. **Tests**: deterministic small fixtures (6–12 users) with hand-checkable expected rankings; property tests for invariants (score in [0,1], reasons ≤ 3, filters hold).
