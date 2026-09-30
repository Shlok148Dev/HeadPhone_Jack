# Sprint board

Owner: Orchestrator (founder directive: no agents unless necessary). Story IDs from SRS v4.0.

## Sprint 4 — Realtime gateway and the friends' feed
Goal: friends' Live, Recent and Top cards on Home, updating without refresh, honest when a source is delayed.

### In progress
- S4-01 Feed API `GET /api/v1/feed` (JNG-05-01, BR-02 ordering, privacy/blocks, degraded flag, cursor) + Top from Mongo
- S4-02 Realtime gateway: JWT handshake, `friends:{id}` rooms from `/internal/users/{id}/friends`, stream consumers (`events:listen` → `feed:update` with per-viewer privacy via core-api), presence (JNG-05-02)
- S4-03 Home: Live now shelf, filter chips (All, Live), everyone grid, live updates, degraded line (JNG-05-03, 05-06, 05-07, 05-08)
- S4-04 Open in my app (JNG-05-04) using recording links + platform search fallback
- S4-05 Presence-driven adaptive polling (Tech Bible 2.3)

### Done
- Sprint 0–3: see STATE.md
