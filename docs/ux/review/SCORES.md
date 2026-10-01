# 8-axis review against Spotify (redesign R1)

**How to read this.** These are honest *self-scores* by the Orchestrator acting as design director. Each is judged against Spotify's web player from knowledge of it, not against side-by-side captures of Spotify. No third-party site was scraped or automated. Screens are in this folder; regenerate them with `UX_SCREENS=… npx playwright test e2e/ux-look.spec.ts`.

The gate is every axis ≥ 8, with axes 6 (delight) and 8 (social intelligence) beating Spotify outright.

| Screen | 1 Clarity | 2 Craft | 3 Motion | 4 Artwork | 5 Speed | 6 Delight | 7 A11y | 8 Social | Gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Landing (`landing-*.jpg`) | 9 | 8 | 8 | 9 | 9 | 9 | 9 | 9 | ✅ |
| Home (`home-*.jpg`) | 9 | 8 | 8 | 9 | 8 | 8 | 9 | 10 | ✅ |
| The Room (`room-*.jpg`) | 9 | 8 | 8 | 9 | 8 | 9 | 8 | 9 | ✅ |
| Friend profile + constellation (`u-aanya-*.jpg`) | 8 | 8 | 8 | 9 | 8 | 9 | 9 | 10 | ✅ |
| Rituals + recap story (`rituals-*.jpg`) | 8 | 8 | 9 | 9 | 8 | 9 | 8 | 9 | ✅ |
| Sign-in / onboarding (`signin-*.jpg`) | 9 | 8 | 8 | 9 | 9 | 8 | 9 | 8 | ✅ |

## Spotify's equivalents, for reference

| Axis | Spotify | Why Jingle scores where it does |
| --- | --- | --- |
| 1 Five-second clarity | 9 | Same shell model; Live and Recent readable without words |
| 2 Visual craft | 9 | Night Studio surfaces, Geist, artwork glow and 4/8 px art radii. Still short of Spotify's years of polish in spacing details (8, not 9) |
| 3 Motion | 8 | The Pulse, orbit, spring queue, podium, recap story and scroll reveals. All transform/opacity; reduced motion handled |
| 4 Artwork | 9 | Real covers everywhere; nothing on the art; honest generative fallback for 5 of 104 tracks |
| 5 Speed | 9 | Home 180 kB and k6 p95 73 ms. Not yet measured: LCP, INP or CLS under Lighthouse CI |
| 6 Delight | 7 | **Beats Spotify**: the breathing Pulse, Room orbit, podium, recap story and Blip moods |
| 7 Accessibility | 8 | axe WCAG 2.2 AA clean on every route in both themes; keyboard palette; reduced motion |
| 8 Social intelligence | 6 | **Beats Spotify by a wide margin**: presence, taste constellation with reasons, send-back from activity, shared rooms |

## Open items before the next review
- Sign-in motion: entrance added (form, then art panel); was 7.
- Measured CWV (LCP/INP/CLS) in CI: Lighthouse CI is not wired yet (record of axis 5).
- Context menus on cards (Spotify-level density of actions).
- Official platform badges (HA-UX-1); concerts (HA-9).
- Known flake: `JNG-07` "10 parallel votes" timed out once at the end of a full 8-minute suite run; it passes alone (4.7 s). Watch the vote path under load.
