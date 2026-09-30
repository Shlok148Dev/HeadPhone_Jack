# Sprint board

Owner: Orchestrator (founder directive: no agents unless necessary; advance sprint to sprint through S11). Story IDs from SRS v4.0.

## Sprint 8 — Blends and live sessions
Goal: a shared playlist that explains itself, and a live listening room whose queue the group steers together.

### To do
- S8-01 Blend model + generator (Tech Bible 6.2) for 2–6 friends or a circle; trainable/analysable data only (JNG-07-01)
- S8-02 One-line reason per track from facts members may see (JNG-07-02)
- S8-03 Pin tracks; regenerate keeps pins (JNG-07-03)
- S8-04 Save to my platform where its API allows; honest "not available" otherwise (JNG-07-04)
- S8-05 Live session: host starts, invites friends or a circle; Redis queue `sess:{id}:queue` + version (JNG-07-05)
- S8-06 Add to queue (optionally anonymous), one up/down vote per track, live re-order over `/rt` (`queue.delta`) (JNG-07-06, 07-07)
- S8-07 Host leaves → next longest-present participant hosts; rejoin gets current versioned queue (JNG-07-08, 07-09)
- S8-08 UI: Blends list + Blend page (reasons, pins, regenerate), Session room (queue, votes, presence), start/join flows; demo blend + session

### Done
- Sprint 0–7: see STATE.md
