# Redesign status (R1, "Night Studio")

_Last updated: 2026-10-01_

| Area | State | Notes |
| --- | --- | --- |
| Artwork service and real-art seed | ✅ | 104-track catalogue; 99 tracks and 79/79 artists with real covers; 5 honest misses use the generative design |
| Tokens, type, grain, radii | ✅ | Night Studio palette; Geist; contrast tests pass |
| Pulse and FeedCard | ✅ | Nothing on artwork; destination-app action |
| Shell (Live now, Friend activity, ⌘K, active marker) | ✅ | Home 156 kB after the polish pass (D-PERF-01) |
| Home (hero, Sent to you, Your Blends, Spotify module) | ✅ | Lazy, with reserved hero height |
| Landing page | ✅ | Server-rendered covers, CSS scroll reveals |
| The Room | ✅ | Ambient field, orbit, spring queue |
| Taste Constellation | ✅ | Friend profile |
| Recap story, podium with covers | ✅ | `/rituals?story=1` |
| Onboarding split-screen with live art | ✅ | `FocusShell` + `ArtPanel`; staggered entrance (form, then art), static under reduced motion |
| Friend profile artwork-tinted header | ✅ | Ambient from the current cover, Pulse at 96 px |
| Concerts | ✖ | Not built (needs a Ticketmaster key; HA-9) |
| Official platform badges | ⏸ | HA-UX-1; text badges meanwhile |
| Blip as an animated state machine (Rive) | ⏸ | SVG poses plus CSS motion for now (no Rive dependency or asset pipeline yet) |
| 90-second tour recording | ✅ | `artifacts/ux/jingle-tour.webm` (70 s, not committed); regenerate: `UX_TOUR=1 npx playwright test e2e/ux-tour.spec.ts --output=../../artifacts/ux/tour` |

Scores against Spotify: `review/SCORES.md`.

## Polish pass (R1.1)

- **Artwork:** 103 of 104 demo songs and all 79 artists now have real covers (was 99). Cover Art Archive is the second source (D-ART-07), and stricter artist matching rejects same-titled namesakes (D-ART-08). Silver Linings is in neither catalogue, so it stays generative.
- **Groups:** Circles show a real cover mosaic built from members' plays, filtered through privacy. Blends no longer draw avatars on artwork (D-ART-09). Circle tiles no longer hover-scale.
- **Friends:** the list shows the Pulse, the song now or last played, the freshness label and send-back, with an icon "more" menu.
- **Phones:** `sm` is now 640 px (D-DS-08). Search is icon-only, recap and battles stack, filter chips scroll sideways in one row, and the activity label stays on one line.
- **Small details:**
  - first-name greeting;
  - solid selected chip (brand moments ≤ 3);
  - recap card coloured by the month's top cover, with "estimated" copy;
  - secondary buttons for share, skip and season;
  - in-field password eye fixed (D-DS-06);
  - honest gateway-error copy (D-COPY-01).
- **Speed:** about 25 kB less JS on every route (D-PERF-01). Cover Art Archive images are served from our cache (3 s → 6 ms).
- **Bug fixed along the way:** the web container's image cache was never writable (`EACCES` on `.next/cache`, running as `node`). The Dockerfile now creates it, and a named volume keeps it across rebuilds. The a11y suite also got faster (5.1 → 2.3 min) now that covers don't stall the page.
- **Repo:** 148 files normalised from CRLF to LF. They had been written by editing scripts on Windows; `.gitattributes` already asked for LF.
