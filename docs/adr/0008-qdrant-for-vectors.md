# ADR-0008: Qdrant for taste vectors

- Status: Accepted (Technical Bible 1.3; Technology Stack 4.2)
- Date: 2026-09-29

Qdrant runs in Compose from Sprint 0, as the kickoff requires. Collection `taste_vectors` (128 dimensions, cosine) with payload `{discoverable, age_band}` for filtered nearest-neighbour search. For the 10-user pilot the suggestion job falls back to NumPy brute force if Qdrant is unreachable.
