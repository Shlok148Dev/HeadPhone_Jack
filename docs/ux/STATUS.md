# Redesign status (R1, "Night Studio")

_Last updated: 2026-10-01_

| Area | State | Notes |
| --- | --- | --- |
| Artwork service and real-art seed | ✅ | 104-track catalogue; 99 tracks and 79/79 artists with real covers; 5 honest misses use the generative design |
| Tokens, type, grain, radii | ✅ | Night Studio palette; Geist; contrast tests pass |
| Pulse and FeedCard | ✅ | Nothing on artwork; destination-app action |
| Shell (Live now, Friend activity, ⌘K, active marker) | ✅ | Home still 180 kB |
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
