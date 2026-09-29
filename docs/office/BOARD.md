# Sprint board

Owner = who builds it. Founder directive: the Orchestrator builds; agents only when necessary. Story IDs from SRS v4.0.

## Sprint 3 — Social graph and privacy
Goal: friends can find each other, connect, and control exactly who sees what; blocks override everything.

### To do
- S3-01 Friendship model (ordered pair), requests send/accept/decline/cancel, duplicate-request merge, 30/day limit — JNG-02-02
- S3-02 Search by username / display name; invite link + QR that auto-sends a request — JNG-02-01, JNG-02-07
- S3-03 Remove friend (activity hidden at once) — JNG-02-03
- S3-04 Block (both ways, within 5 s, no notification) and report user — JNG-02-04, JNG-12-01
- S3-05 Policy helpers real (`are_friends`, `is_blocked_either_way`, `can_view_activity`); internal friends list for realtime
- S3-06 Privacy UI: visibility, exact time, Private mode (1 h / 8 h / until off), blocked list — JNG-02-05, JNG-02-06
- S3-07 Friends page (requests, search, invite) + onboarding friends step — JNG-01-12
- S3-08 Seed demo friendships and a few pending requests (ADR-0010)

### In progress

### Review

### Done
- Sprint 0–2: see STATE.md (setup, accounts, ingest core, demo, web shell, Companion, Jingle Connect routes)
