# S10 Rituals, notifications and trust: review (Orchestrator, 2026-10-01)

**Scope**
- Backend: `rituals/*` (battles, season, recap, close and recap jobs), `notifications/*` (centre, prefs, quiet hours, push, cap), `moderation/*` (reports context, actions, appeals, audit, flags, budgets proxy, allowlist), ingest-ml usage counters and `/internal/budgets`, notify call sites unified, reports extended to circles and notes, suspension permission, mute checks, configurable auth rates, demo seeds.
- Web: `/rituals` (battle cards, nominate, vote, podium reveal, season, skip, recap flip card, share link, save as image), `/recap/[token]`, `/notifications`, `/settings/notifications` (push opt-in, per-type, quiet hours, cap), `/settings/account` (standing and appeals), `/staff` console, TopBar bell, `public/sw.js`, CSP `worker-src 'self'`.

## Checked
- **Gherkin "Late vote".** A vote at 21:00:05 is rejected with "Voting has closed" and the leaderboard is unchanged.
- **Battle integrity.** One nomination each, 3 votes each, never on your own song, row lock on the budget, idempotent close job, notifications sent on results, a skipped week excluded from the season.
- **Privacy.**
  - Nominations are anonymous while voting.
  - Recap sharing is opt-in and revocable, and the public page shows a first name only.
  - Direct-Spotify listens are excluded from recaps.
  - Push payloads hold only a title and an in-app URL.
  - The service worker opens only same-origin URLs.
- **Notifications.**
  - Push is off until the browser allows it.
  - Per-type controls work.
  - Quiet hours span midnight and follow the person's time zone.
  - The cap holds at 5 a day while in-app still gets everything.
  - Dropped subscriptions are cleaned up.
- **Trust.**
  - The queue is staff-only and shows context.
  - A mute blocks posting but not reading.
  - A suspension locks the app except standing and appeals.
  - A ban deactivates the account.
  - Moderators can't act on themselves and must give a reason.
  - Overturned appeals lift the action.
  - Flags, allowlist and moderation changes are all audited.
  - The allowlist cap of 5 matches Spotify's development mode.
- **E2E (three new).**
  - Battle card, nominate, season table, recap flip, share link opened publicly, then revoked.
  - Bell, centre, read state, settings saved.
  - Moderator warns from the queue, the audit log shows it, the member appeals.
  - axe is clean on each page.
- **Bugs found and fixed.**
  - A recap card wrapper with zero width (it only had absolute children).
  - An `audit()` kwarg collision with `action`.
  - The refresh rate limit throttling normal browsing behind one NAT.
- **Coverage.** rituals, notifications and moderation are at 91%.

## Deferred (recorded)
- Weekly "what your circles played" digest (JNG-09-09, Should), email digest (JNG-11-05, Could), track comment threads (JNG-11-06, Should), send streaks (JNG-09-07, Could).
- Concerts (EP-10): need a Ticketmaster key (a human signup); not built in the pilot, listed in HUMAN_ACTIONS as optional.
- Push is verified up to the browser subscription and the pywebpush call (mocked); real delivery needs a browser outside automation.

Verdict: **ship**.
