# Sprint board

Owner: Orchestrator (founder directive: no agents unless necessary; advance sprint to sprint through S11). Story IDs from SRS v4.0.

## Sprint 7 — Sends and mixtapes
Goal: send a friend a song (or a 5–8 track mixtape) that opens on their own app, and see honestly whether it landed.

### To do
- S7-01 Recommendation + items + recipients models; `POST /recommendations` (track or mixtape, note ≤ 280, friends and/or circle; limits) (JNG-06-01, 06-02)
- S7-02 Open on the recipient's platform: resolved links or search fallback, never a route word (JNG-06-03, Gherkin "Cross-platform send")
- S7-03 Status Sent → Delivered → Viewed → Played; Played only from the recipient's own listens after the send (JNG-06-04)
- S7-04 Inbox `GET /inbox` + unread count; reactions and track replies (JNG-06-06, 06-07)
- S7-05 Discovery credit when the sent artist enters the friend's top artists (JNG-06-05)
- S7-06 UI: Send sheet from any card (NowPlayingBar Send, FeedCard send), mixtape builder, Inbox page + Sent tab with statuses; demo sends

### Done
- Sprint 0–6: see STATE.md
