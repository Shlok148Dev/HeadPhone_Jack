# S6 Circles — review (Orchestrator, 2026-09-30)

Scope: `services/core_api/circles/*`, `jingle_ml/circles.py`, `jingle_ml/tasks.suggest_circles`, `core_api/policy.share_circle`, `core_api/internal.py`, `feed/views.py` (`?circle=`), `seed_demo`; web `lib/circles.ts`, `(app)/circles`, `(app)/circles/[id]`, `circles/join/[token]`, Home circle chips.

## Checked
- **BR-08 never auto-join:** the only ways into a circle are accepting an invite addressed to you, tapping Join on a link, or creating it. Suggested circles create the circle for the one person who chose it and send invites to the rest (Gherkin "Suggested circle is never auto-joined").
- **Limits:** 50 members held under concurrency (`select_for_update` on the circle row + `member_count` check constraint); 20 circles per user; Gherkin "Full circle" (preview says full, POST 409 "This circle is full", nobody added).
- **Privacy:** non-members get 404 for circle, circle feed and `/feed?circle=` (existence never confirmed). Blocked members are hidden from member list and circle feed. "Only circles I choose" visibility now resolves via real `share_circle`.
- **Links:** only the sha256 of the token is stored; links expire after 7 days; unknown/expired → same 404 copy.
- **Roles:** owner-only role changes and hand-over; admins remove members but not admins; owner must hand over before leaving; last member out closes the circle.
- **Realtime:** watch list = friends ∪ circle co-members − blocks; membership changes publish `friendship.changed` so rooms re-sync.
- **UI:** axe clean on list, circle page and join page; ambient header uses the seeded gradient with white text on deep tones; one-shot `?invite=1` (found in E2E: reload reopened the sheet — fixed).
- **Budgets:** Home 180 kB (at budget; circle chips cost ~0.3 kB), circle pages 176–178 kB.

## Found and fixed during the sprint
- Invite sheet reopened on reload (`?invite=1` persisted) → replaced URL after opening.
- Suggestions E2E depended on demo state consumed by earlier runs → `seed_demo` resets the demo login's own pending requests and dismissals on each start.

## Deferred (recorded)
- Battle schedule editing UI (JNG-04-07 part): stored and PATCH-able now; the editor ships with battles in S10.
- Circle cover upload: generative covers only (no uploads until moderation console, S10).
- Discoverable circles browse ("people at my college"): flag stored; discovery surface after S7.

Verdict: **ship**.
