# ADR-0004: MongoDB time-series collection for listens

- Status: Accepted (Technical Bible 1.3, first five ADRs)
- Date: 2026-09-29

Listens go to a MongoDB time-series collection `listens` (timeField `played_at`, metaField `meta` = `{user_id, platform, via}`, granularity minutes, `expireAfterSeconds` = 13 months ≈ 34,187,400 s). Rationale per Technology Stack 4.1: it isolates the heaviest write path from transactional data. TimescaleDB remains a valid alternative.
