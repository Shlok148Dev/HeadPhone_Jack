# ADR-0023: Rituals, notifications and trust (Sprint 10)

- Status: Accepted
- Date: 2026-10-01

## Battles (JNG-09-01…04, 08)

1. **One battle per circle per IST week.** It is created lazily from the circle's `battle_schedule` (default Mon 18:00 / Fri 18:00 / Sun 21:00). Times are frozen when the battle is created, so a schedule change applies from the next week.
2. **What people see when.**
   - Before Monday's nominations open, people see last week's results.
   - Nominations are anonymous while voting is open, so people judge the song, not the friend. Names are revealed with the results.
3. **Voting rules.** One nomination each, changeable until voting opens. Three votes each, never on your own nomination, one per nomination.
   - The battle row is locked while a vote is counted, so the 3-vote budget holds under concurrency.
   - A vote at or after `closes_at` gets "Voting has closed" (Gherkin).
4. **Results.** A close job runs every minute, so the leaderboard is published within 5 minutes and members are notified. Ranks are dense; ties go to the earliest nomination.
5. **Skipped weeks.** An admin can skip the current week. The season table counts wins over the last 8 battles that actually ran, so a skip doesn't break the season.

## Recap (JNG-09-05/06)

6. **Built on the 1st and 2nd at 06:00**, well inside the 48-hour target, from analysable listens plus Jingle-native activity (sends, received songs, battle wins).
7. **Sharing is off by default.** It is an explicit per-recap token that can be revoked. The public page shows only the card and a first name.
8. **Image export** is drawn in the browser on a canvas, so no third-party renderer is involved.

## Notifications (JNG-11-01…04, 07)

9. **Storage.** Rows live in PostgreSQL (`notifications`), not MongoDB as CONTRACTS §2 first suggested, because unread counts and per-user queries are relational. CONTRACTS is updated.
10. **One entry point.** Every notification goes through `notifications.services.notify`. Each call writes an in-app row and sends a realtime `notify` hint. Web push is sent only if all of these hold:
    - the person subscribed in their browser (push is off by default);
    - the type allows push;
    - it is outside quiet hours (default 23:00–08:00 in the person's own time zone);
    - they are under the daily cap (5, raisable to 20, counted in Redis per IST day).
11. **Web push uses VAPID keys** that are generated locally into `.env` (no third-party approval). Without keys, push is reported as unavailable. Subscriptions that the browser has dropped (404/410) are deleted. Push payloads carry only a title and an in-app URL.

## Moderation and admin (JNG-12-01…06, 08)

12. **Reports** cover users, circles you're in, and notes on songs sent to you. The queue shows the reported content, the responsible account, other reports on it, and past actions.
13. **Actions and their effects.**

    | Action | Effect |
    | --- | --- |
    | Warn | A notification. |
    | Mute | Blocks new public content (sends, notes, queue adds, nominations, circle names). |
    | Suspend | 403 everywhere except reading your own standing, appealing and signing out. |
    | Ban | Deactivates the account. |

    Every staff action writes an append-only `audit_log` entry, including flag changes and allowlist edits.
14. **Appeals.** One per action. Overturning an appeal lifts the action, and reactivates the account if it was a ban.
15. **Admin console (`is_staff`).**
    - Feature flags can be toggled.
    - Per-source budgets and live usage come from ingest-ml's `/internal/budgets`, backed by per-minute counters in Redis.
    - The Spotify tester allowlist is kept in the DB, capped at 5, and combined with `SPOTIFY_ALLOWLIST` from `.env`.
16. **Demo moderator.** Demo mode seeds a staff login (`mod@jingle.local`, demo password) and one open report.

## Also decided this sprint

17. **Auth rate limits are configurable.** Refresh moved from 30/min to 120/min per IP, because every page load refreshes and a pilot group may share one campus NAT. Login stays at 10/min per IP+email. Local `.env` raises both for E2E runs.
