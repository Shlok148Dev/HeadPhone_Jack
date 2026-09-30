# ADR-0019: Friend suggestions implementation (Sprint 5)

- Status: Accepted
- Date: 2026-09-30

## Decisions
1. **Formula exactly as Technical Bible 5.2** (Adamic–Adar 0.35, taste cosine 0.30, context 0.15, contacts 0.10, local 0.10). Contact matching (JNG-03-04, Should) is not built in the web pilot: no phone contacts in a browser; weight stays 0.
2. **Taste vectors use `trainable` listens only** plus the member's own onboarding picks (TF-IDF → SVD when > 128 features). Direct-Spotify API data (Policy III.13/III.14) and Last.fm data (BR-04) never enter them. Enforced in `jingle_ml.data.listen_filter` with a test on real documents.
3. **Hard filters twice:** before scoring (Tech Bible 5.1) and again when suggestions are read (blocks, pending/accepted friendships, 90-day dismissals, discoverability), so changes apply immediately rather than at the next nightly run.
4. **Reasons** come only from facts the viewer may see: mutual-friend count or name (the viewer's own friend), shared artists only if the candidate is not private, same college/city (opt-in profile fields). No reason → no suggestion.
5. **Compute where the libraries live:** the Celery `ml` queue (worker image with NumPy/scikit-learn/Qdrant client) computes; the API reads Redis `sug:{user}` (NFR-PERF-08) and only enqueues by task name. Nightly 03:00 IST, within seconds of a new friendship or taste change, and after demo seeding.
6. **Qdrant** receives the vectors (ADR-0008) for ANN at scale; neighbours are computed exactly with NumPy at pilot size.
7. **Evaluation** (`manage.py eval_suggestions`): Recall@20, coverage, unsafe pairs, logged to MLflow or `artifacts/ml/`. Demo run: Recall@20 0.80, unsafe 0, coverage 0.37 (small, tightly connected demo world).
