# S8 Blends and live sessions: review (Orchestrator, 2026-09-30)

**Scope**
- Backend: `blends/*` (engine, services, API, regenerate task), `listening/*` (sessions, queue, votes, sweep), `core_api/internal.SessionMemberView`.
- Realtime: `session:join` / `session:leave`, `queue:delta` routing, session presence.
- Web: `lib/live.ts`, `/blends`, `/blends/[id]`, `/sessions/[id]`, PeoplePicker, OpenLink, circle page entry points.
- Seed: demo Blend.

## Checked
- **Tech Bible 6.2 constraints** have unit tests: shared tracks beat one-sided favourites, ≤ 2 per artist, share cap, pins first, reason templates.
- **Privacy.**
  - A member's plays are used only when everyone else in the Blend may see them. Covered by tests with strangers inside one Blend and with circle-only visibility.
  - The circle owner's default "friends" visibility correctly excludes them from a non-friend's view.
  - Direct-Spotify listens are excluded.
  - Anonymous adds never serialise the adder.
  - Joining a room is checked against core-api for membership and blocks.
- **Gherkin JNG-07-07/09.**
  - The rules and the versioned broadcast are covered in pytest.
  - True concurrency: 10 parallel votes via the API on PostgreSQL all count (E2E).
  - Reconnect: the version gap triggers a REST refetch (`applyDelta` unit test). The room is rejoined on every socket connect.
- **Live UX (E2E, two browsers).**
  - The guest sees the host's song appear without a refresh.
  - An anonymous add shows "added anonymously".
  - A second tap withdraws a vote (one vote each).
  - The new order reaches the host live.
  - When the host leaves, the guest becomes host and can Play next.
- **Honesty.** Save to platform says it isn't available yet (JNG-07-04). An empty Blend says "Not enough listening to blend yet."
- **A11y.** axe is clean on the Blend page and the session room.
- **Budgets.** Home stays at 180 kB. `/blends` is 181 kB and `/sessions/[id]` is 179 kB (no budget set; noted for S11).
- **Coverage.** `blends` + `listening` are at 91%.

## Found and fixed
- Friend-request E2E helper assumed the send response carried the request id (it returns the person). The helper now reads the recipient's incoming list.
- A circular import between `core_api.internal` and `listening.views` was fixed by keeping the internal check in `core_api/internal.py`.

## Deferred (recorded)
- LightFM candidates for Blends (the artist stand-in is documented in ADR-0021) → with S9/S11 models once enough native data exists.
- Session chat (Should): hidden, per UX_SPEC.
- p95 ≤ 1 s fan-out under 100 sessions × 50 voters → k6 session storm in S11.
- Rename Blend: not built (Leave and Regenerate are).

Verdict: **ship**.
