# ADR-0021: Blends and live sessions (Sprint 8)

- Status: Accepted
- Date: 2026-09-30

## Blends
1. **Algorithm as Technical Bible 6.2**
   - Pool: each member's top 100 tracks from the last 90 days.
   - Affinity: play count ÷ the member's top count.
   - Group utility: mean − 0.5 × standard deviation.
   - Size: 30 tracks, with ≤ 40 % per supplying member and ≤ 2 per artist. Resolved recordings win ties.
   - The share cap is relaxed only when a small group lacks variety. The artist cap never is.
   - **LightFM candidates are replaced** by an artist-level stand-in: 0.5 × the member's affinity for the track's artist. This is the R-B decision; LightFM stays deferred until there is enough Jingle-native interaction data to train on, per BR-04.
2. **Privacy gate.** A member's plays shape a Blend only if *every other member* may see that member's activity (`policy.can_view_activity`, so blocks, Private mode and visibility all apply). Members who are left out are listed honestly on the Blend. Only analysable listens are used, so direct-Spotify API data is excluded (BR-03).
3. **Reasons** are deterministic templates built from facts the room can see: who plays the track, or who plays a lot of its artist. The optional LLM rephrase (Tech Bible 6.5) is not used in the pilot. A track without a reason is dropped, so every track carries one (JNG-07-02).
4. **Pins** survive regeneration and read "Pinned by {name}" (JNG-07-03).
5. **Save to platform (JNG-07-04)** is reported as unavailable. No zero-approval write path exists in the pilot: Spotify needs a playlist scope plus the allowlist, and the other platforms have no approved write API. Users can open each song or copy the list. This will be revisited when HA-1 keys exist.

## Live sessions
6. **PostgreSQL is the source of truth** (`sessions`, `session_participants`, `session_queue`, `session_votes`).
   - Every change runs `INCR sess:{id}:ver` and publishes `queue.delta {session_id, version, state}` on `events:domain`.
   - The realtime gateway forwards it to the `session:{id}` room.
   - The Redis ZSET from Tech Bible 3.4 is unnecessary at pilot size: the queue is ordered by an indexed query (score desc, then added time).
7. **Writes go over REST** (the Tech Bible's REST fallback), and each carries an idempotency key.
   - The socket is used only to join and leave rooms: `session:join` is checked against core-api `/internal/sessions/{id}/members/{user}`.
   - The socket also receives versioned state.
   - Clients drop deltas older than their current version. On reconnect they rejoin the room and refetch REST state (JNG-07-09).
8. **Votes:** one ±1 per person per entry (unique constraint). A 0 withdraws the vote. The entry row is locked while its score is recomputed, so concurrent votes all count. This is proven with 10 parallel votes on PostgreSQL in E2E.
9. **Anonymous adds** hide the adder from the room. `submitted_by` is kept for rate limits and moderation and is never serialised (JNG-07-06).
10. **Presence and hand-over.**
    - The gateway sets `sesspres:{sid}:{uid}` (60 s TTL) every 20 s while the room is open.
    - A 30 s sweep hands the host role to the longest-present online participant when the host drops off. An explicit leave does the same immediately (JNG-07-08).
    - Rooms with nobody present for 10 minutes end.
11. **Joining:** a session is open to invited friends, or to all members of the chosen circle. Anyone blocked either way with the host can't join.
