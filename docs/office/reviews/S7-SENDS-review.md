# S7 Sends and mixtapes: review (Orchestrator, 2026-09-30)

**Scope**
- Backend: `services/core_api/sends/*`, `seed_demo._seed_sends`, beat entries.
- Web: `lib/sends.ts`, `lib/send.tsx`, `components/app/SendSheet.tsx`, `(app)/inbox`, AppShell Inbox button and Send bar, FeedCard Send on Home and the circle page.

## Checked
- **Recipients.** Friends only, or circles the sender belongs to (non-members get 404). Blocked people are dropped when sending and hidden in both Received and Sent. A reply goes only to the original sender.
- **Limits.** Notes are ≤ 280 characters. A send is 1 song or a 5–8 song mixtape, with no duplicate songs. Up to 50 recipients and 200 sends a day.
- **JNG-06-03 (Gherkin).**
  - Server: the Apple Music link resolves when it exists; otherwise the item carries only a search link.
  - Client: `openTarget` says "Not found on Apple Music" and offers "Search in Apple Music" (unit test).
  - No route words appear in the Inbox (E2E).
- **Statuses.**
  - Sent → Delivered (the recipient fetched it) → Viewed (the row was on screen, or a reaction) → Played (the recipient's own listen after the send, within 30 days).
  - Direct-Spotify listens are ignored because only `analytics_allowed` listens count (BR-03). Listens from before the send never count.
  - Verified against live Mongo documents on the stack.
- **Discovery credit.** Top 20 for the last 30 days, within 60 days of the send, and absent for the 6 months before it. A negative test covers an artist the recipient already knew.
- **Realtime.** `notify` types `send`, `send_status` and `send_reaction` invalidate the inbox queries. Circle invites now refresh their own query.
- **A11y.** axe is clean on the Inbox (both tabs) and the Send sheet. The Send sheet's region was renamed "Recipients" so it no longer shares a name with the "Send to" field (E2E caught the duplicate).
- **Budgets.** The Send sheet and the Home suggestions shelf load lazily, keeping Home at 180 kB. `/inbox` is 176 kB.
- **Coverage.** The `sends` app is at 93% (12 tests including the Gherkin scenarios).

## Found and fixed
- The success toast never showed: `mutate` callbacks are dropped after the optimistic close unmounts the sheet. It now uses `mutateAsync`.
- `next/dynamic` added about 1 kB to the shared layout; replaced with `React.lazy`.

## Deferred (recorded)
- Streak for sends (JNG-09-07, Could) → S10 rituals.
- Push notifications for new sends → S10 notifications (in-app badge and live refresh now).
- Song search covers only songs already known to Jingle. A MusicBrainz search is a possible S11 addition within its 1 req/s limit.
- `/friends` first load is 182 kB with no budget set; review in the S11 performance pass.

Verdict: **ship**.
