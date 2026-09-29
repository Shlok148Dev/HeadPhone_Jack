---
name: jingle-design-system
description: Jingle's design system — tokens, components, motion, card states (Live, Recent, Top, Hidden, Degraded), dark and light theme rules, Blip mascot usage, with do and don't examples. Use this whenever you build or change ANY screen, component, style, animation or copy in apps/web or the companion extension popup, even a small tweak, and whenever you review UI screenshots. Also use it when choosing colours, fonts, spacing, icons or artwork for Jingle.
---

# Jingle design system

The reference implementation is the `/design` route (`apps/web/src/app/design/page.tsx`). Tokens live in `packages/design-tokens/` and are exposed as CSS variables in `apps/web/src/app/globals.css`. Primitives live in `apps/web/src/components/ds/`. Feature screens compose these; they don't invent new colours, radii or shadows. That keeps both themes and the brand coherent, and lets one token change restyle everything.

## Identity

| Token | Value | Use |
| --- | --- | --- |
| `--brand-violet` | #8B6BFF | Start of the brand gradient |
| `--brand-cyan` | #3FE7D8 | End of the brand gradient |
| `--gradient-brand` | 135deg violet → cyan | Primary buttons, focus accents, logo mark, selected chips |
| `--live` | #FF6B5E (coral) | **Only** Live: Live badge, equaliser bars, Live shelf title dot. Nothing else is coral, so coral always means "playing right now". |
| `--bg` | dark #08080B / light #F7F7FA | Page |
| `--surface-1..3` | stepped elevations | Cards, sheets, popovers |
| `--text`, `--text-muted` | ≥ 4.5:1 on their surfaces in both themes | |

Fonts: Bricolage Grotesque (display: page titles, hero, numbers on recap), Inter (all UI text), JetBrains Mono (data labels: timestamps, scores, counts, freshness labels). Loaded through `next/font/google`.

Spacing on a 4 px grid; radius scale `--r-sm 8`, `--r-md 12`, `--r-lg 20`, `--r-pill 999`. Touch targets ≥ 44×44 px.

## Card states (FeedCard)

| State | Visual | Label example (JetBrains Mono) |
| --- | --- | --- |
| LIVE | Coral ring on artwork, animated equaliser bars, coral "Live" pill | `Live on Spotify` |
| RECENT | Normal card, muted timestamp | `20 min ago on Apple Music` |
| TOP | Card with "Top this month" chip, stacked mini-artworks | `Top this month` |
| HIDDEN | Avatar + name only, soft lock glyph, no track | `Hidden` |
| Degraded | Last known state, true timestamp, small amber "delayed" tag | `2 h ago on YouTube Music · delayed` |

Labels come from the server (`freshness_label`); the client never builds them, so the no-false-Live rule lives in one place.

## Honesty rules that are visual rules

- Never show route words (ListenBrainz, Last.fm, scrobble, extension, bridge, Companion, route) on cards, profiles or notifications. Credits live only on Settings → Connections. (ADR-0002, BR-14.)
- Never render Live styling unless `state === "LIVE"`.
- Never ship grey placeholder squares: `<Artwork>` falls back to `<GenerativeCover seed=…>` (deterministic gradient + shapes from the recording id).
- Platform names are text badges (`<PlatformBadge platform="APPLE_MUSIC" />` → "Apple Music"). No platform logos, wordmarks, icons, brand fonts or brand colours for badges; badges use neutral surface colours.

## Motion

Library: `motion` (`motion/react`). Presets in `apps/web/src/lib/motion.ts`:

- `spring.soft` (stiffness 260, damping 30) for card entry, staggered 40 ms.
- `spring.snappy` (400, 32) for presses and chips.
- Shared element: `layoutId={"card-" + id}` from card to detail.
- Equaliser: 3–4 bars, 0.9–1.3 s loops, only on Live.
- Podium reveal (battles) and flip-card (recap) are in `components/ds/`.

Everything reads `useReducedMotion()`; when true, animations become instant opacity changes. Only animate `transform` and `opacity` (60 fps, no layout shift). Skeletons match the real content's shape.

## States every screen needs

default · loading (skeleton) · empty (`<Blip pose="wave|sleepy" />` + one clear action) · error (plain words + retry) · degraded (cached, honest time). Both themes. 360–1920 px. Keyboard operable with visible focus ring (`--focus-ring` = 2 px gradient outline).

## Blip

`<Blip pose="idle|wave|cheer|sleepy" size={…} />` — an original SVG character (rounded note-blob with eyes). Use: empty states (wave, sleepy), success (cheer), loading long jobs (idle). Never as decoration on busy screens.

## Do / don't

- Do: gradient only on the primary action per view. Don't: gradient text blocks or multiple gradient buttons.
- Do: coral only for Live. Don't: coral for errors (errors use `--danger`).
- Do: ambient background from artwork (`useArtworkColor`) on profile/circle/Blend headers, with a translucent blurred header. Don't: full-saturation artwork colour behind body text.
- Do: shelves scroll horizontally with snap and arrow buttons for mouse users. Don't: hide overflow without a keyboard path.

## Review checklist (paste into the design review)

- [ ] Dark and light, 1440 px and 390 px screenshots
- [ ] Contrast ≥ 4.5:1 for text; focus visible on every control
- [ ] All five states present where applicable
- [ ] No route words; no platform brand assets; no grey placeholders
- [ ] Coral used only for Live; gradient only for the primary action
- [ ] Reduced-motion respected
