---
name: jingle-design-system
description: Jingle's design system ("Night Studio") — tokens, components, motion, artwork rules, card states (Live, Recent, Top, Hidden, Degraded), the Pulse, dark and light theme rules, Blip mascot usage, Spotify content separation, with do and don't examples. Use this whenever you build or change ANY screen, component, style, animation or copy in apps/web or the companion extension popup, even a small tweak, and whenever you review UI screenshots. Also use it when choosing colours, fonts, spacing, icons or artwork for Jingle.
---

# Jingle design system: Night Studio

The intimacy of a dim studio at 2 a.m.:

- warm-black surfaces;
- real artwork glowing like lit vinyl;
- coral used as a recording light, for Live only;
- violet → cyan as the brand's light, used sparingly.

It is not a neon dashboard, purple SaaS, glass everywhere, or a Spotify clone.

The reference implementation is the `/design` route. The source files are:

- **Tokens:** `packages/design-tokens/src/{index.ts,tokens.css}`, kept in sync and contrast-checked by tests.
- **Primitives:** `apps/web/src/components/ds/`.
- **Decisions:** `docs/ux/DECISIONS.md`, one line each.

Feature screens compose these and never invent colours, radii or shadows.

## Colour

| Token | Dark / Light | Rule |
| --- | --- | --- |
| `--bg`, `--surface-1..3` | #0A090C → #252129 / #F6F2EC → #E5DED4 | Warm steps, never pure grey. Light is a designed paper theme, not an inversion |
| `--gradient-brand` | violet #8B6BFF → cyan #3FE7D8 | **At most 3 brand moments per screen**: the primary action, the active nav marker, one hero accent |
| `--live` | coral #FF6B5E | **Only** Live: the Pulse ring, equaliser bars, the Live chip, the Live shelf dot. Nothing else is coral |
| Ambient | `artwork_colors.ambient_dark/light` from the Artwork service | Hero and detail backgrounds take colour from the real cover. Already contrast-checked to 4.5:1 for `--text`; use `ambientStyle()` (`lib/ambient.ts`) |

## Type

- **Bricolage Grotesque** for display (tracking −0.025em, big confident sizes on hero and detail headers).
- **Geist** for UI text (ADR-0024, chosen over Inter for dense lists).
- **JetBrains Mono** for data: times, counts, scores, freshness labels, with tabular numerals.
- Headings use `text-wrap: balance` and body text uses `pretty`.

## Shape and depth

- 4 px grid.
- Radii:
  - **artwork 4 px small / 8 px large** (all providers);
  - cards 12 px;
  - sheets and modals 20 px;
  - pills full.
- Depth comes from layered surfaces, plus `.jg-art-glow` (a soft shadow in the cover's own colour, set via `--art`).
- Film grain sits on `body::before` (≈3 %).
- Frosted glass is used only for the top bar, sheets and the now-playing bar.

## Artwork (hard rules)

- **Real covers only**, from the Artwork service (`/api/v1/artwork`; iTunes Search API, then MusicBrainz + Cover Art Archive; MusicKit once a token exists). Payloads carry `artwork_url`, `artwork_small` and `artwork_colors`.
- When no confident match exists, use `<GenerativeCover>`: muted, clearly a design, never a fake photo, never grey.
- **Never put text, badges, controls or logos on artwork. Never crop, distort, recolour or animate it.** Motion and Live signals live *around* it (container, shadow, the person's Pulse).
- Group faces (Blends, Circles) use `<CoverMosaic covers seed>`; avatars go below it, never on it.
- No hover scale on artwork containers (scaling the box scales the art).
- Store URLs and colours only; never commit image files.

## The Pulse (presence without words)

`<Pulse state="live|recent|none">` wraps an avatar:

- **live:** a breathing coral ring plus halo.
- **recent:** a still neutral ring.

The difference must read at a glance. Live comes only from the server (`state === "LIVE"`, under 90 s, not degraded); the client never computes it.

## Card states (FeedCard)

| State | Visual | Label (mono, verbatim from server) |
| --- | --- | --- |
| LIVE | coral ring around (not on) the art, Live Pulse, coral `Live` chip beside the name | `Live on Spotify` |
| RECENT | still Pulse ring, muted time | `20 min ago on Apple Music` |
| TOP | 2×2 cover stack, "Top" pill | `Top this month` |
| HIDDEN | avatar, lock glyph, no track | `No plays yet` / `Hidden` |
| Degraded | last known state, true time, amber "delayed" | `2 h ago on YouTube Music · delayed` |

The open action shows the destination app's name ("Apple Music"). The full sentence ("Search in Apple Music: Kasoor") is its accessible name.

## Spotify content separation (Spotify Developer Terms)

- Data from the Spotify Web API (`attribution === "SPOTIFY"`, allowlisted testers only) appears **only** in its own attributed module ("From Spotify" plus "Data from Spotify"). It is never interleaved in mixed shelves.
- Listening that reaches Jingle any other way is Jingle's data. It appears in mixed shelves with the platform named as text ("Live on Spotify").

## Platform marks

Official marks (D-BRAND-02): `<PlatformMark platform>` shows the icon, and `<PlatformLabel>` / `<PlatformBadge>` show the icon plus the name. Amazon Music is a wordmark, so its name is sr-only. Rules:
- Unmodified and in brand colour.
- At text size, beside the name or the server's label; never inside a sentence.
- Never on artwork.
- In feed labels, the mark sits *outside* the verbatim `freshness_label` span.
- Guideline check before launch: HUMAN_ACTIONS HA-UX-1.

## Motion

Uses `motion/react` plus `lib/motion.ts` presets.

**Timings:**

| Kind | Duration |
| --- | --- |
| Hover and press | 120–180 ms |
| Small UI changes | 180–260 ms |
| Page and shared-element transitions | 300–450 ms |

**Rules:**

- Use springs for anything the user drags or votes on: the session queue uses `layout` spring re-ordering.
- Never ease-in for entering UI; never bounce or elastic.
- Cards cascade with 30–40 ms staggers.

**Landing page:**

- Scroll reveals are CSS scroll-driven (`.jg-reveal`, visible by default).
- The cover wall drifts (`.jg-drift`, paused on hover).

**Signature moments:**

- **The Room:** cover hero on an ambient field, avatars orbiting (`.jg-orbit`).
- **Podium:** rises 3, 2, 1.
- **Recap:** a full-screen story with progress bars (`RecapStory`).
- **Taste Constellation:** overlapping fields of real artist images.

**Discipline:** only animate `transform` and `opacity`. Under reduced motion everything is static or instant.

## States every screen needs

Every screen needs all five:

- default;
- loading (skeleton shaped like the content);
- empty (Blip plus one clear action);
- error (plain words plus retry);
- degraded (cached data, honest time).

Every screen also works in both themes, at 360–1920 px, and with the keyboard (visible focus, 44×44 px targets).

## Shell

- **Left rail:** nav with a gradient active marker; "Live now" list at 1024–1439 px.
- **Top bar:** search pill that opens the ⌘K/Ctrl+K command palette; inbox; bell; theme; avatar.
- **Bottom now-playing bar.**
- **Right "Friend activity" panel** at ≥ 1440 px.

## Do / don't

- Do: one gradient primary per view. Don't: gradient text blocks or several gradient buttons.
- Do: real covers with their own colour glow. Don't: neon placeholders, blurred copies of artwork as backgrounds, or text on covers.
- Do: coral for Live only. Don't: coral for errors (use `--danger`).
- Do: honest copy ("Sound comparison unavailable"). Don't: fake numbers or invented Live.

## Review checklist

- [ ] Dark and light; 1440 px and 390 px; real covers visible
- [ ] Nothing on artwork; artwork radii 4/8 px
- [ ] Contrast ≥ 4.5:1 (including over ambient fields); focus visible
- [ ] All five states; no route words; Spotify API content separated and attributed
- [ ] Coral only for Live; ≤ 3 brand-gradient moments
- [ ] Reduced motion respected; Home first-load JS ≤ 180 kB
