# Jingle UX Specification (web phase)

- Owner: ux-researcher. Status: v1.0, binding for every feature screen. Last updated 2026-09-29.
- Inputs: PRD §6, SRS v4 §5.1 and §6 (EP-01 to EP-13), `docs/PLAN.md`, ADR-0002 (no route words), ADR-0003 (Companion push first), ADR-0007 (display-only Spotify), ADR-0011 (18+ from birth year), `docs/architecture/CONTRACTS.md` §7 (FeedCard), `.claude/skills/jingle-design-system/SKILL.md`.
- Reference build: the `/design` route renders every component and state in this document, in both themes. If this spec and `/design` disagree, raise it with design-system-engineer; this spec wins until changed.
- Conventions: sizes in CSS px; "desktop" means 1440 px wide; "mobile" means 390 px wide. Copy in `code-quotes` is exact and ships as written (i18n keys may wrap it). `{braces}` are variables.

---

## 1. Principles

1. **Familiar shell, Jingle soul.** On first open Jingle should feel like a music app the person already knows: sidebar, shelves, a bar at the bottom. The identity comes from the violet→cyan gradient, Blip, big grotesque type and cards that explain themselves, never from borrowed brand assets.
2. **Honest over impressive.** Coral and equaliser bars appear only when the card's `state === "LIVE"`. A true "2 h ago" beats a fake "Live". A missing capability shows its fallback state quietly, never an error on a card (BR-15).
3. **Explain everything.** Suggestions carry ≤ 3 reasons, Blend tracks carry one reason line, compatibility is never shown without its breakdown (BR-09).
4. **Their app, not ours.** Every track opens on the viewer's own platform. Jingle is the room where friends meet, not a player.
5. **The user is in control.** Every sharing setting is visible, reversible and one step away. Nobody is added to anything without accepting (BR-08).
6. **Calm by default.** Dark theme first. Motion is springy but short, respects `prefers-reduced-motion`, and never moves layout. Live changes are announced politely and throttled.
7. **Every state designed.** Default, loading (content-shaped skeleton), empty (Blip + one action), error (plain words + retry), degraded (cached with the honest time). Both themes, 360–1920 px, keyboard operable, WCAG 2.2 AA.
8. **Routes are invisible.** Cards, profiles, notifications and toasts name only the music platform. Route words (ListenBrainz, Last.fm, scrobble, scrobbler, bridge, extension, Companion, route, token, API) appear only on Settings → Connections (credits and capability notes) and inside the one-time Connect sheet where there is no other way to say it (ADR-0002, BR-14).

---

## 2. Information architecture and navigation

### 2.1 Route map

| Route | Screen | Auth | Shell |
| --- | --- | --- | --- |
| `/` | Landing | public (signed-in users redirect to `/home`) | Marketing shell (no sidebar) |
| `/signin`, `/signup` | Sign in / Sign up | public | Focus shell (centred card) |
| `/onboarding/profile`, `/sources`, `/privacy`, `/friends` | Onboarding steps 1–4 | signed in | Focus shell with stepper |
| `/home` | Home | signed in | AppShell |
| `/friends` (tabs `?tab=requests|suggestions|find`) | Friends | signed in | AppShell |
| `/circles`, `/circles/{id}` | Circles list, Circle page | signed in | AppShell |
| `/blends`, `/blends/{id}` | Blends list, Blend detail | signed in | AppShell |
| `/sessions/{id}` | Live session | signed in | AppShell (NowPlayingBar shows session strip) |
| `/rituals`, `/rituals/battles/{id}`, `/rituals/recap/{yyyy-mm}` | Rituals hub, Battle, Recap | signed in | AppShell |
| `/u/{username}` | Profile (own or friend) | signed in | AppShell |
| `/inbox` (tabs `?tab=received|sent`) | Inbox of sends | signed in | AppShell |
| `/notifications` | Notifications (full page; the bell opens a popover first) | signed in | AppShell |
| `/settings/connections`, `/privacy`, `/notifications`, `/accessibility`, `/data` | Settings | signed in | AppShell with settings sub-nav |
| `/invite/{code}` | Invite landing (friend or circle) | public → sign-up → auto-request | Focus shell |
| `/design` | Design system reference | dev + signed-in staff | Bare shell with theme toggle |

### 2.2 Desktop (≥ 768 px): sidebar

Order is fixed; icons are Jingle's own outline set (Lucide-derived, 24 px, 1.75 px stroke), never platform icons.

1. **Home** (`/home`)
2. **Friends** (`/friends`) — badge: pending request count
3. **Circles** (`/circles`)
4. **Blends** (`/blends`)
5. **Rituals** (`/rituals`) — dot when a battle phase needs you (nominate or vote open, not yet done)
6. **Profile** (`/u/{me}`)

Below a 1 px divider, a **Library** section (Spotify-style library list, our own styling): "Your circles and Blends", filter pills `Circles` `Blends`, then a list of rows (40 px artwork or GenerativeCover, name, secondary line in mono e.g. `12 members · 3 live`). Live count in the secondary line is the only coral in the sidebar, as a 6 px dot before the number, and only when > 0. Footer: `+ New circle` (secondary button, full width).

Sidebar collapse: at 768–1023 px the sidebar is a 72 px **rail** (icon + 11 px label under the icon, library hidden; library reachable via Circles). At ≥ 1024 px it is expanded by default; user can collapse it to the rail with the collapse IconButton (preference stored in `localStorage`, key `jingle.sidebar`).

### 2.3 Mobile (< 768 px): bottom tab bar

Five tabs, 64 px tall + `env(safe-area-inset-bottom)`:

| Tab | Goes to | Notes |
| --- | --- | --- |
| Home | `/home` | |
| Friends | `/friends` | numeric badge for requests |
| Circles | `/circles` | the Circles screen has a segmented control `Circles · Blends` on mobile, so Blends live here |
| Rituals | `/rituals` | dot when action needed |
| You | `/u/{me}` | avatar 24 px instead of an icon |

Settings on mobile: from You → gear IconButton in the profile header. Inbox: from the TopBar tray icon.

### 2.4 TopBar (all breakpoints)

Left to right on desktop: back/forward IconButtons (only in AppShell, history-aware, disabled at ends) · **Search** field (max 480 px, placeholder `Search people, circles, songs`; `/` focuses it) · flexible space · **Inbox** IconButton (tray; badge = unviewed received sends) · **Notifications** IconButton (bell; badge = unread, max `9+`) · **Theme toggle** IconButton (sun/moon; cycles Dark → Light; long-press or right-click offers `Match system`) · **Avatar** menu (Profile, Settings, Keyboard shortcuts, Sign out).

On mobile: page title (Bricolage, 22 px) at left; search IconButton opens a full-screen search sheet; Inbox, Notifications, Theme toggle IconButtons; no avatar (it is the You tab). On scroll, the TopBar gains a translucent background (`--surface-glass`) with 20 px backdrop blur and a hairline bottom border.

### 2.5 Now-playing bar (persistent)

Shows **my** now-playing (never a friend's), with quick Send. Defined in §4.4. On mobile it is a 64 px mini-bar floating 8 px above the tab bar.

### 2.6 Navigation rules

- Every screen has a unique `<h1>` (visually the page title).
- Route changes move focus to the `<h1>` and announce `{Page title}` via the route announcer (Next.js default, kept).
- Back behaviour: detail pages (Circle, Blend, Session, Battle, Profile) show a back IconButton at the left of the ambient header on mobile.
- Deep links from notifications land on the exact object and scroll it into view with a 1.2 s highlight (outline pulse; reduced motion: static outline for 2 s).

---

## 3. Layout grid and breakpoints

Mobile-first CSS; breakpoints are **min-width**. Tokens: `--bp-sm 390`, `--bp-md 768`, `--bp-lg 1024`, `--bp-xl 1440`, `--bp-2xl 1920`. The 360 row is the floor we test at (no min-width query).

| Width | Nav | Sidebar width | Content columns | Margin (each side) | Gutter | Content max width | Top bar | Now-playing bar | Shelf card width | Cards visible in a shelf |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 360 | Bottom tabs 64 | — | 4 | 16 | 12 | fluid | 56 | 64 mini (above tabs) | 136 | 2 + 28 px peek |
| 390 | Bottom tabs 64 | — | 4 | 16 | 12 | fluid | 56 | 64 mini (above tabs) | 148 | 2 + 38 px peek |
| 768 | Rail | 72 | 8 | 24 | 16 | fluid | 64 | 80 | 160 | 3 + peek |
| 1024 | Sidebar | 240 (rail 72 when collapsed) | 12 | 24 | 20 | fluid | 64 | 80 | 168 | 4 |
| 1440 | Sidebar | 280 | 12 | 32 | 24 | 1600 | 64 | 88 | 184 | 5–6 |
| 1920 | Sidebar | 300 | 12 | 40 | 24 | 1600 (centred in the main canvas) | 64 | 88 | 200 | 6–7 |

Rules:

- Main canvas = viewport − sidebar. Content inside is constrained to max width 1600 and centred; shelves bleed to the canvas edge on the right only (scroll area extends into the margin, first card aligns to the grid).
- Bottom space: the main scroll area has `padding-bottom` = now-playing bar height (+ tab bar + 8 on mobile) + 24 so the last row is never hidden.
- Detail pages (Profile, Circle, Blend, Recap) use Apple-style generous spacing: section gap 48 px desktop / 32 px mobile; ambient header height 340 px desktop, 280 px at 1024, 240 px mobile.
- Dense pages (Home, Friends) use Spotify-style density: section gap 32 px desktop / 24 px mobile; shelf title row 40 px.
- Quick-send grid: 2 columns (360–767), 3 columns (768–1023), 4 columns (1024–1439), 4 columns (≥ 1440) with 2 rows visible; tiles 56 px tall (desktop 64).
- Card grids (Circles list, Blends list, Friends suggestions): `repeat(auto-fill, minmax(W, 1fr))` with W = 160 (mobile), 184 (768+), 200 (1440+).
- Touch targets ≥ 44 × 44 at every width, including the shelf arrow buttons and chip hit areas (chips are 32 px tall visually with an 8 px transparent hit-slop above/below on touch).
- No horizontal page scroll at 360 px. Only shelves, chip rows and carousels scroll horizontally.
- Layout shift budget: CLS < 0.02. Images always have explicit aspect-ratio boxes; skeletons match final dimensions.

---

## 4. Component inventory

All primitives live in `apps/web/src/components/ds/`. Each is shown on `/design` in every variant and state, dark and light. "States" always include hover, active (pressed), focus-visible and disabled for interactive parts unless noted; focus-visible is always `--focus-ring` (2 px outline, 2 px offset).

### 4.1 AppShell

- **Anatomy:** skip link (`Skip to main content`, first focusable, visible on focus) → Sidebar/rail (≥ 768) → TopBar → `<main id="main">` scroll container → NowPlayingBar → BottomTabBar (< 768) → Toast region → live-announcer region.
- **Variants:** `app` (default), `focus` (auth/onboarding: logo top-left, centred 480 px card, no nav), `marketing` (landing), `bare` (`/design`).
- **States:** default; `offline` (TopBar shows a 32 px banner under it: `You're offline. Showing what we had at {HH:mm}.`, `--warning` icon, no coral); `realtime-reconnecting` (same banner slot: `Reconnecting…` with spinner; auto-dismiss on reconnect with toast `Back online`).
- **A11y:** landmarks `nav[aria-label="Main"]`, `header`, `main`, `aside[aria-label="Now playing"]`, `nav[aria-label="Tabs"]` on mobile. Only one `main`. Page scroll happens in `main`, and `main` keeps `tabindex="-1"` for skip-link focus.

### 4.2 Sidebar

- **Anatomy:** logo mark (gradient Blip-note glyph + "Jingle" set in Bricolage 700, 22 px) · nav list (6 items: icon 24 + label Inter 15/600) · divider · Library header (`Your circles and Blends`, IconButton `+`) · filter pills · library list (virtualised past 30 rows) · collapse IconButton at bottom.
- **Variants:** expanded (240/280/300), rail (72).
- **States:** item default (`--text-muted`), hover (`--text`, `--surface-2` bg), active route (`--text`, 4 px gradient bar on the left edge, `aria-current="page"`), with badge, with action dot (gradient dot, 8 px), loading library (5 row skeletons), empty library (`No circles yet` + ghost button `Create a circle`).
- **A11y:** `<nav aria-label="Main">` with a `<ul>`; library is a separate `<nav aria-label="Library">`. Rail labels stay in the DOM (visually 11 px) so names are never icon-only. Badges have visually hidden text: `, 3 pending requests`.

### 4.3 TopBar

- **Anatomy:** see §2.4. Height 64 (desktop) / 56 (mobile).
- **Variants:** `solid` (default at scrollTop 0 on non-ambient pages), `glass` (after 8 px of scroll, or always on ambient-header pages: `--surface-glass` + `backdrop-filter: blur(20px) saturate(140%)`; if `backdrop-filter` unsupported, fall back to `--surface-1` at 96% opacity).
- **States:** search idle / focused (width expands 320→480 with `spring.snappy`, results popover under it) / results loading (3 row skeletons) / no results (`No one or nothing called "{q}". Try a username or a song title.`).
- **A11y:** search is a `combobox` with `aria-expanded`, `aria-controls` listbox, result groups `People`, `Circles`, `Songs` as `role="group"` with labels. Theme toggle `aria-label="Switch to light theme"` / `"Switch to dark theme"` and `aria-pressed` not used (it is an action, not a state). Notifications button label includes the count: `Notifications, 4 unread`.

### 4.4 NowPlayingBar

- **Anatomy (desktop, 80/88 px):** left zone (min 280): Artwork 56 (coral 2 px ring if my state is LIVE) · title (Inter 15/600, 1 line) · artist (13, muted) · freshness label (mono 12, from the server, e.g. `Live on Spotify`). Centre zone: **Send** button (primary gradient, icon + `Send`) · `React` IconButton · `Open in my app` IconButton (external-link icon, label `Open in Spotify` built from `platform`). Right zone: `Private mode` toggle chip (`Private` with eye-off icon when on) · `Who can see this` IconButton (opens privacy popover) · sharing status text (mono 12, muted): `Friends can see this` / `Hidden from everyone until 22:40`.
- **Mobile mini (64 px):** Artwork 40 · title/artist stack · Send IconButton (gradient fill, 44 px) · chevron to expand into a Sheet showing the full desktop content.
- **Variants:** `live` (EqualiserBars 16 px beside the label), `recent` (label e.g. `12 min ago on Apple Music`), `idle` (nothing played in 24 h: Blip `sleepy` 32 px + `Nothing playing. Play something in your app and it shows up here.`; Send disabled), `private` (content dimmed to 60%, lock glyph, label `Private mode · until {HH:mm}`; Send still enabled — sharing a track is an explicit act), `not-connected` (no sources: `Connect your music to see what you're playing` + secondary button `Connect`, opens Settings → Connections), `session` (inside `/sessions/{id}`: shows session name and `Up next: {title}` instead of Send).
- **States:** loading (artwork + two text line skeletons), error (keeps last known content, label gets the Degraded `delayed` tag; no error text in the bar).
- **A11y:** `<aside aria-label="Now playing">`. Track changes are **not** announced (the user caused them). Send is reachable by the global shortcut `s`.

### 4.5 Shelf

A horizontal scroller of cards with snap and arrow buttons.

- **Anatomy:** header row (40 px): title (Bricolage 22/600 desktop, 20 mobile) with optional leading 8 px coral dot (Live shelf only) and optional count (mono 13, muted) · `See all` ghost link (right) · previous/next IconButtons (desktop ≥ 1024 and any fine pointer; 36 px visual, 44 px hit). Track: `display:flex; gap: var(--gutter); overflow-x:auto; scroll-snap-type:x mandatory; scroll-padding-inline: var(--margin)`; each card `scroll-snap-align:start`. Edge fades: 32 px gradient mask on the side that has more content.
- **Behaviour:** arrow scrolls by `floor(visibleCards) * (cardWidth + gutter)`; arrow disabled (hidden with opacity 0, still in DOM with `aria-disabled`) at the ends. Wheel-shift and trackpad horizontal scroll work natively. Scrollbar hidden visually on fine pointers but the track remains keyboard scrollable.
- **Variants:** `cards` (FeedCard/CircleCard), `people` (Avatar 96 + name), `compact` (SuggestionCard), `live` (title prefixed with coral dot, cards live-update and re-order: newly Live cards enter at the front with `card.enter`).
- **States:** loading (skeleton cards × visible count + 1), empty (per shelf; most shelves hide when empty except those listed in §5), error (inline row: `Couldn't load {shelf title}.` + ghost `Retry`), degraded (cards render cached content; header gains mono tag `Updated {n} min ago`).
- **A11y:** `<section aria-labelledby="{shelf-title-id}">`; track is `role="list"` with `aria-label="{title}"`, cards are `role="listitem"`. Roving tabindex: only one card in the tab order; ←/→ move focus between cards and scroll it into view; Home/End jump to first/last; Tab leaves the shelf. Arrow buttons have `aria-controls` the track and labels `Scroll {title} left/right`; they are `tabindex="-1"` because arrow keys already cover keyboard users (pointer affordance only).

### 4.6 FeedCard

The heart of Jingle. Data: FeedCard contract (CONTRACTS.md §7). The client renders `freshness_label` verbatim and never builds it.

- **Anatomy (shelf size W × auto):** Artwork (W × W, radius `--r-md`) with overlays: top-left `LiveBadge` (LIVE only); bottom-right hover/focus action cluster (desktop) · below artwork (8 px gap): row 1 Avatar 20 + friend display name (Inter 13/600, 1 line); row 2 track title (Inter 15/600, 1 line, ellipsis); row 3 artist (Inter 13, muted, 1 line); row 4 freshness label (JetBrains Mono 12/500, muted; `--live-text` colour when LIVE) + optional `delayed` tag · optional attribution line (`attribution === "SPOTIFY"`): mono 11 `Data from Spotify` + link-back (see §11).
- **Row size (feed list at mobile):** 72 px row: Artwork 56 · text stack · trailing `More` IconButton.
- **Actions:** primary click on card → Track detail sheet (shared element: artwork `layoutId="card-{id}"`). Action cluster: `Send` (paper-plane), `Open in {my platform}` (external link), `React` (smile; opens 6-emoji picker), `More` (menu: `Start a Blend with {name}`, `View profile`, `Hide {name}'s activity from Home`, `Report`). On touch: no hover cluster; `More` IconButton is always visible and contains all actions; tap on card opens the Track detail sheet.
- **Variants by state:**

| State | Visual | Label (from server) |
| --- | --- | --- |
| LIVE | 2 px coral ring around artwork (`--live`), LiveBadge top-left with EqualiserBars, label text in `--live-text` | `Live on Spotify` |
| RECENT | No ring; label muted | `20 min ago on Apple Music`, `3 h ago on YouTube Music`, `2 d ago on Amazon Music`, `Recently on Spotify` (friend hides precise time) |
| TOP | Artwork shows a 2×2 stack of the friend's top 4 artworks (each W/2, 2 px gap); chip `Top this month` (neutral surface chip) replaces the track rows with "{top artist} and 3 more" | `Top this month` |
| HIDDEN | No artwork: a `--surface-2` square with the friend's large Avatar (W × 0.5) centred and a soft lock glyph 16 px; rows show name only | `Hidden` |
| Degraded (any state with `degraded: true`) | Last known state rendered normally but LIVE is never shown while degraded (server guarantees; client also asserts); mono tag `delayed` in `--warning-text` on `--warning-bg` pill after the label, separated by ` · ` | `2 h ago on YouTube Music` + tag `delayed` |
| Unresolved recording (`recording.id === null`) | GenerativeCover seeded by `friend.id + raw title`; `Open in my app` becomes `Search in {platform}` | unchanged |

- **Other states:** loading (skeleton: square + 4 lines at 90/70/50/40% width), updating (label cross-fades; card does not move unless order changes, then `layout` spring), reacted (small emoji bubble 20 px bottom-left of artwork, `spring.snappy` pop), error (never shown on a card; failures happen at the shelf level).
- **A11y:** card is an `<article>` with `aria-labelledby` title and `aria-describedby` label. Accessible name reads: `{name}: {title} by {artist}. {freshness_label}{, delayed}`. The equaliser is `aria-hidden`. Action cluster buttons are always in the DOM (visually revealed on hover and `:focus-within`). Tab order inside a card: the card's main button (opens Track detail), then Send, Open, React, More. In a shelf, only the focused card's controls are tabbable (roving tabindex, §4.5). Hidden cards expose `{name}. Activity hidden.`

### 4.7 LiveBadge and EqualiserBars

- **LiveBadge anatomy:** pill 22 px tall, `--live` background, `--on-live` text (`#1A0705`, 6.98:1), 8 px horizontal padding: EqualiserBars (12 × 10) + `LIVE` (Inter 11/700, letter-spacing 0.06em). Sizes: `sm` 18 px (list rows), `md` 22 px (cards), `lg` 28 px (session header).
- **EqualiserBars:** 4 bars, each 2 px wide, 1 px radius, 1 px gap; animate `scaleY` 0.25↔1 from bottom origin, durations 0.9 s, 1.3 s, 1.1 s, 1.0 s, `ease-in-out`, infinite, alternate, random 0–300 ms start offset per card (seeded by card id so SSR/CSR match). On `--live` pill the bars use `--on-live`; standalone they use `--live`.
- **Rules:** render only when `state === "LIVE"` and `degraded === false`. Pause animations when the card is off-screen (IntersectionObserver) and when `document.hidden`.
- **Reduced motion:** static bars at heights 40/100/70/55%.
- **A11y:** badge text `Live` is read as part of the card label; bars `aria-hidden="true"`.

### 4.8 PlatformBadge (text)

- **Anatomy:** neutral pill 20 px tall, `--surface-3` background, `--text-muted` text, Inter 12/500, 8 px padding. Content is the display name only: `Spotify`, `Apple Music`, `Amazon Music`, `YouTube Music`. `UNKNOWN` renders nothing.
- **Never:** logos, glyphs, brand colours, brand fonts or platform-specific shapes. No green, red, pink or blue per platform.
- **Variants:** `inline` (text only, no pill, used inside sentences), `pill`.
- **A11y:** plain text; no `title` tooltip needed.

### 4.9 Artwork and GenerativeCover

- **Artwork anatomy:** `aspect-ratio: 1`, radius per size (`--r-sm` ≤ 56 px, `--r-md` ≤ 200, `--r-lg` above), `object-fit: cover`. Sources in order: `recording.artwork_url` (Cover Art Archive, Apple Music, or Spotify-with-attribution) → GenerativeCover.
- **Loading:** first paint shows the GenerativeCover (not grey) under the `<img>`; the image fades in (`opacity` 0→1, 180 ms) on load. No blur-up of third-party art.
- **Error:** `onError` keeps the GenerativeCover; never a broken-image icon; never a grey square.
- **GenerativeCover:** deterministic from `seed` (recording id, or `artist|title` for unresolved, or circle/Blend id). Algorithm: hash → hue pair from the brand-friendly range (violet 250–280° to cyan 170–185°, plus a third accent hue anywhere except 0–20°, which is reserved-looking coral) → background linear gradient at hashed angle → 3–5 shapes (circles, rounded bars, arcs) at hashed positions with 30–70% opacity → optional initials (first letters of the title, Bricolage 700, 40% of size, `--on-cover` white with 30% black text-shadow). Rendered as inline SVG, cached per seed.
- **A11y:** decorative inside cards (`alt=""`, the card already names the track). Standalone (detail headers) alt = `Cover art for {title} by {artist}`; generative alt = `Pattern cover for {title}`.

### 4.10 Avatar and AvatarStack

- **Avatar:** sizes 20, 24, 32, 40, 56, 96, 128. Circle. Image or initials on a GenerativeCover seeded by user id. Optional presence ring: coral 2 px ring only when that friend is LIVE (Live-only rule holds). Optional status dot is not used (no "online" concept).
- **AvatarStack:** up to 4 avatars overlapped by 30% with a 2 px `--bg` border, then `+{n}` bubble (mono 12). Accessible name: `Aanya, Dev, Riya and 5 others`.
- **States:** loading (circle skeleton), error (initials).

### 4.11 Chip and FilterChips

- **Chip anatomy:** 32 px tall, radius pill, 12 px padding, Inter 13/500, optional leading icon 16 or leading 8 px coral dot (Live chip only), optional trailing count (mono 12).
- **Variants:** `filter` (selectable), `input` (removable, trailing ×), `suggestion` (tap to apply), `status` (non-interactive; e.g. `Delivered`), `tag` (non-interactive, e.g. `Top this month`).
- **States:** default (`--surface-2`, `--text-muted`), hover (`--surface-3`, `--text`), selected (gradient background, `--on-brand` text, check icon for multi-select), pressed (scale 0.96, `spring.snappy`), disabled (40% opacity).
- **FilterChips row:** horizontal scroller with 8 px gap, same keyboard pattern as a shelf. Home order: `All` · `Live` (coral dot; count of Live friends) · one chip per circle (sorted by most recent activity) · `+ {n} more` overflow chip at > 8 circles (opens a menu). Single-select.
- **A11y:** single-select chips are a `role="radiogroup"` with `role="radio"` items and `aria-checked`; multi-select use `aria-pressed` toggle buttons. Arrow keys move and select for radiogroup.

### 4.12 Button

- **Sizes:** `sm` 32 (desktop dense only), `md` 40, `lg` 48 (mobile default for primary CTAs). Hit area ≥ 44 always (`sm` gets hit-slop).
- **Variants:**
  - `primary`: `--gradient-brand` background, `--on-brand` text (`#0B0B12`, ≥ 5.27:1 across the gradient), Inter 15/600. **One primary per view.**
  - `secondary`: `--surface-2` background, `--text`, 1 px `--border`.
  - `ghost`: transparent, `--text`; hover `--surface-2`.
  - `danger`: `--danger-bg` background, `--on-danger` text; used only for destructive confirms (Delete account, Remove friend, Block).
- **States:** hover (primary: gradient shifts 10% via `background-position`; others: surface step up), pressed (scale 0.97 via `spring.snappy`), focus-visible (ring), loading (label kept for width, replaced visually by a 16 px spinner; `aria-busy="true"`; button disabled), disabled (40% opacity, `aria-disabled`), success flash (optional, 600 ms check icon for optimistic actions).
- **A11y:** text labels always; icon-only uses IconButton.

### 4.13 IconButton

- 44 × 44 hit, 36 × 36 visual (desktop) / 40 × 40 (mobile), 20–24 px icon. Variants `ghost` (default), `filled` (`--surface-2`), `brand` (gradient; only for the mobile Send). Required `aria-label`; tooltip on hover/focus after 500 ms showing the same text plus the shortcut, e.g. `Send (S)`. Toggle IconButtons use `aria-pressed`.

### 4.14 Tabs

- Underline tabs, 44 px tall, Inter 15/600; active tab has a 3 px gradient underline that slides between tabs (`layoutId="tab-underline"`, `spring.snappy`). Mobile: scrollable if they overflow. Optional count (mono 12).
- **A11y:** WAI-ARIA tabs pattern: `role="tablist"`, arrows move, automatic activation (content is local or cached). Tab state mirrored in the URL `?tab=`.

### 4.15 Sheet and Dialog

- **Dialog** (desktop centred, max width 560, radius `--r-lg`, `--surface-1`, scrim `--scrim`): title (Inter 20/600), body, footer actions right-aligned (primary last). Confirmation dialogs for destructive actions name the object: `Remove Aanya as a friend?`.
- **Sheet:** bottom sheet on < 768 (drag handle 36 × 4, snap points 50% and 92%, swipe down to dismiss), right-side panel (420 px) on ≥ 768 for Send, Track detail and Connect.
- **Motion:** `sheet.enter` (§6). Reduced motion: fade only.
- **A11y:** `role="dialog"`, `aria-modal="true"`, labelled by title; focus moves to the first focusable (or the title if none); focus trapped; Esc closes (except while a submit is in flight); focus returns to the invoker. Sheets have a visible `Close` IconButton (drag is never the only way).

### 4.16 Toast

- Bottom-centre on desktop (above NowPlayingBar + 16 px), bottom above mini-bar on mobile. Max 1 visible, queue of 3. 4 s default; 6 s with an action; persistent for errors with Retry.
- **Variants:** `neutral`, `success` (Blip `cheer` 24 px for social wins, e.g. `Sent to Aanya`), `error` (danger icon, never coral), `undo` (action `Undo`, e.g. `Suggestion dismissed · Undo`).
- **A11y:** container `role="status"` `aria-live="polite"`; error toasts `role="alert"`. Hover/focus pauses the timer. Toasts never hold the only way to do something.

### 4.17 Skeletons

- Colour `--skeleton` with a shimmer (`--skeleton-shine` linear gradient sweeping via `transform: translateX`, 1.4 s linear infinite). Reduced motion: no shimmer, static fill.
- Shapes match the component exactly: FeedCard (square + 4 lines), CircleCard, Avatar circles, text lines at 90/70/50%. The skeleton for a page is the page's layout with real headers (shelf titles render immediately; they are static copy).
- Appear only after 150 ms of waiting (avoid flash); minimum display 300 ms once shown.
- **A11y:** skeleton container `aria-busy="true"` on the section, and a visually hidden `Loading {section}` once.

### 4.18 EmptyState with Blip

- **Anatomy:** Blip (size 120 desktop / 96 mobile, pose per context) · title (Bricolage 24/600) · one-line body (Inter 15, muted, max 44 ch) · **one** action (primary if it is the page's main action, otherwise secondary). Centred in the section, max width 400.
- **Blip poses:** `wave` (first-time, invite), `sleepy` (nothing happening right now), `cheer` (success, all caught up), `idle` (long job in progress).
- **Blip itself:** original SVG — a rounded, slightly squashed note-blob in the brand gradient with two oval eyes and a small tail curl; no mouth in `idle`, smile in `wave`/`cheer`. Idle breathing (scale 1↔1.03, 3.2 s) and one-shot pose motion on mount. Reduced motion: static pose.
- **A11y:** Blip is `aria-hidden`; the title is a heading at the correct level.

### 4.19 ErrorState

- **Anatomy:** danger-tinted icon (circle-alert 32, `--danger-text`), title (Inter 18/600), body (plain words, what happened and what to do), action `Try again` (secondary) and optional `Go home` (ghost). Mono line `Ref {request_id}` (muted, selectable) for support.
- Never coral, never Blip (Blip is for empty and success). Never blames the user.
- **A11y:** container `role="alert"` when it replaces content after a user action; plain region when on first load.

### 4.20 HeroCarousel (Home)

- **Anatomy:** slides at 21:9 (desktop, max height 360) / 4:5 (mobile). Each slide: background (artwork collage or GenerativeCover, blurred 40 px behind + crisp artwork on the right third) · ambient colour wash · eyebrow (mono 12 uppercase, e.g. `NEW BLEND`, `BATTLE RESULTS`, `YOUR SEPTEMBER RECAP`) · title (Bricolage 40/44 desktop, 28/32 mobile, max 2 lines) · subtitle (Inter 15) · one CTA (primary on the active slide) · AvatarStack of people involved. Controls: prev/next IconButtons (desktop), pagination dots (8 px; active dot is a 24 px gradient pill) and a pause/play IconButton.
- **Content types (priority order):** unviewed battle result (Sun 21:00 → Tue), new recap (1st–7th), new or regenerated Blend, pending circle suggestion (`Make a circle with these 5?`), featured session in progress in your circle. Max 5 slides; with 1 slide no controls; with 0 slides the hero hides (no empty state; the page starts with Live now).
- **Behaviour:** auto-advance every 7 s; pauses on hover, on focus within, when not visible, and permanently after any manual interaction in that visit. Autoplay is off entirely under reduced motion. Swipe on touch. Snap scroll.
- **Loading:** one slide skeleton at the final aspect ratio.
- **A11y:** APG carousel pattern: `section aria-roledescription="carousel" aria-label="Highlights"`, slides `role="group" aria-roledescription="slide" aria-label="2 of 4"`; rotation control first in tab order (`Pause highlights` / `Play highlights`); live region `aria-live="off"` while auto-rotating and `polite` when user-driven.

### 4.21 QuickSendGrid

- **Purpose:** send one of my recent tracks in two taps (YouTube Music "quick picks" idea, pointed at friends).
- **Anatomy:** header `Quick send` + mono subtitle `From your last 24 h`; grid (§3) of tiles: Artwork 48 · title/artist stack · trailing Send IconButton (paper-plane, ghost). Max 8 tiles (2 rows × 4 desktop).
- **Interaction:** tile click or Send → Send sheet pre-filled with the track; keyboard `Enter` on a tile does the same.
- **States:** loading (8 tile skeletons), empty (`Nothing played in the last day.` + ghost `Search for a song to send`), not-connected (tile area replaced by ConnectPlatformCard compact: `Connect your music to send what you play`), degraded (tiles render; subtitle `Updated {n} min ago`).
- **A11y:** `role="list"`; each tile is one button with name `Send {title} by {artist}`.

### 4.22 SuggestionCard

- **Anatomy (card, 184 wide):** Avatar 96 · display name (Inter 15/600) · `@username` (mono 12, muted) · reasons list (max 3, each Inter 13 with a 14 px leading glyph: people for mutuals, note for taste, circle for shared context, map-pin for college/city) · actions: `Add` (secondary, becomes `Requested` status chip with `Cancel` on hover) and `Dismiss` IconButton (×, label `Dismiss {name}`).
- **Rules:** exactly the server's reasons, never more than 3; if the server sends 0 reasons the card is not rendered (no unexplained suggestions). Reasons never show a Private-mode person's tracks.
- **States:** default, requesting (optimistic `Requested`), request failed (revert + toast `Couldn't send the request. Try again.`), dismissed (card collapses with `card.exit`; toast `Won't suggest {name} for 90 days · Undo`).
- **A11y:** `<article>` labelled by name; reasons in a `<ul>`.

### 4.23 CircleCard

- **Anatomy:** cover (square, circle artwork or GenerativeCover seeded by circle id, radius `--r-lg`) with bottom scrim · name (Inter 16/600) · mono line `{n} members` · AvatarStack (up to 4) · Live row when > 0: coral dot + `{n} live now` in `--live-text`. Optional ritual chip: `Vote open`, `Nominate`, `Results in` (neutral chips).
- **Variants:** `member`, `suggested` (dashed 1 px `--border-strong` outline, label `Suggested for you`, actions `Accept invite` / `Ignore`), `invite` (pending invite: `Join` primary-in-card, `Decline` ghost), `full` (disabled Join, text `This circle is full`).
- **A11y:** whole card is a link to the circle; inner buttons stop propagation and are separate tab stops.

### 4.24 BlendTrackRow

- **Anatomy (64 px desktop / 72 mobile):** index (mono 13, muted, 32 px column) · Artwork 48 · title (Inter 15/600) / artist (13 muted) · **reason line** (Inter 13, muted, always present, e.g. `Both of you played this in the last month`, `Aanya's top track, new to Dev`) · contributor AvatarStack (max 3, 20 px) · pin IconButton (`aria-pressed`) · `Open in {my platform}` IconButton · `More`.
- **States:** default, hover (`--surface-2`), pinned (pin filled, gradient pin icon; mono tag `Pinned`), regenerating (non-pinned rows cross-fade to skeletons; pinned rows stay), unresolved on my platform (`Open` becomes `Search in {platform}` + tooltip `Not found on {platform}`).
- **A11y:** list is a `<ol>`; each row an `<li>` with the reason in `aria-describedby`.

### 4.25 SessionQueueRow

- **Anatomy (64 px):** Artwork 48 · title / artist · `Added by {name}` or `Added anonymously` (13 muted) · score (mono 15/600, centred between votes) · Upvote and Downvote IconButtons (chevron-up/chevron-down, `aria-pressed`) · host-only `Remove` in `More`.
- **States:** default; my vote up (up icon filled gradient); my vote down (down icon filled `--text`); now playing (top row, larger 80 px, LiveBadge-free — sessions are not Live listening data — uses a gradient left bar and `Now` tag); pending vote (optimistic score change, icon pulses once; reverts with toast `Vote didn't go through. Try again.`); reordered (row moves with `layout` spring `spring.soft`); one vote per member per track, own additions included (JNG-07-07); tapping the same arrow again removes the vote; `Voting closed` state when the session ends.
- **A11y:** vote buttons labelled `Upvote {title}, current score 4`. Reorders are announced politely at most once every 5 s: `{title} moved to position 2`. Focus stays on the row the user voted on even if it moves.

### 4.26 BattlePodium

- **Anatomy:** three columns (2nd, 1st, 3rd left→right), podium blocks heights 60/100/40% of 240 px (desktop) / 160 px (mobile); on top of each: Artwork 96 (1st: 128), title, nominator Avatar + name, votes (mono). Below: full leaderboard list (rank mono, artwork 40, title, nominator, votes). Season table link `Season table`.
- **Reveal sequence:** 3rd rises, then 2nd, then 1st (see `podium.reveal`), then confetti of 24 gradient dots (1.2 s) and Blip `cheer` beside 1st if the viewer nominated a top-3 song.
- **States:** pre-reveal (`Results at 21:00 Sunday` with countdown in mono, `aria-live="off"`), revealing, revealed, replay (`Replay reveal` ghost), no nominations (empty), tie (shared rank, blocks equal height, label `Tied`).
- **A11y:** the podium is `aria-hidden` decoration over the real leaderboard `<ol>` which is always in the DOM; the reveal announces once: `Results: 1st {title} nominated by {name}, {votes} votes…`. Reduced motion: final layout shown immediately.

### 4.27 RecapFlipCard

- **Anatomy:** 9:16 card (max 360 × 640 desktop; full width − 32 on mobile), radius `--r-lg`, ambient gradient from the month's top artwork. Front: month (Bricolage 56), headline stat (`2,340 minutes`, Bricolage 72 numbers), Blip. Back faces (sequence of cards): Top 5 tracks · Top genre shift (`Lo-fi ↑ 12%`) · Top friend match (Avatar 96 + CompatibilityMeter mini + reason) · Platforms used (PlatformBadges with share %).
- **Interaction:** click/tap/Enter/Space flips to the next face (`recap.flip`); ←/→ move between faces; progress dots show position. `Share` primary (image PNG generated server-side or link), `Download image` secondary.
- **States:** loading (card skeleton + `Putting your month together…` with Blip `idle`), not ready (`Your recap arrives by the 2nd.`), not enough data (empty), error.
- **A11y:** each face is also rendered as a text section for screen readers (`aria-hidden` on the 3D wrapper, real content in a visually hidden list), flip button labelled `Next: Top 5 tracks`.

### 4.28 CompatibilityMeter

- **Anatomy:** ring meter (120 px desktop, 96 mobile) with gradient stroke to `score/100` and the score centred (Bricolage 40, numerals tabular) · label `Taste match` (mono 12) · **breakdown always rendered next to or under it**: up to 3 reason lines, `Shared artists` (AvatarStack-like artwork stack + names, max 5), `Shared genres` (chips), `Sound` (tempo, energy, mood bars) **or** exactly `Sound comparison unavailable`.
- **Rule (BR-09):** the component requires a `breakdown` prop; TypeScript type makes it non-optional; if the breakdown is missing the component renders the loading/error state, never a bare number.
- **States:** loading (ring skeleton + 3 lines), limited data (`We need a couple more weeks of listening to compare you two.` + Blip `sleepy`, no number), error.
- **A11y:** `role="img"` on the ring with `aria-label="Taste match 78 out of 100"`; breakdown is normal text.

### 4.29 ConnectPlatformCard

- **Anatomy:** card (min 160 × 120) with the platform name in Inter 18/600 (PlatformBadge `inline`, **no logo**), one line of what you'll get (`Live and recent plays` / `Recent plays` see §10), and **one** button `Connect {Platform}` (secondary; primary only on the platform the user picked as "most used"). Status footer (mono 12) when connected.
- **States:** `not connected`, `connecting` (button loading, sheet open), `waiting for first play` (`Waiting for your first play…` with idle Blip 24 and spinner), `connected` (`Connected ✓`; mono `First play seen ✓ {time}`), `needs attention` (`Reconnect {Platform}` button, warning text `Your connection expired. Reconnect to keep your plays up to date.`), `unavailable` (feature-flagged off: hidden entirely, per BR-11 for the direct Amazon link; Amazon Music card itself stays because its web player works).
- **Rule:** exactly one button per platform (BR-13). Alternatives (other ways to connect) live inside the Connect sheet, not on the card.
- **A11y:** the button name includes the platform; status changes announced politely once: `Spotify connected. First play seen.`

### 4.30 SettingsConnectionsRow

- The only place where route credits and route words may appear in the steady-state product.
- **Anatomy:** platform name (Inter 16/600) · status chip (`Connected`, `Waiting for first play`, `Needs reconnect`, `Off`) · capability line (Inter 13 muted, e.g. `Live when you play in your browser. Recent plays from your phone.`) · honest note where relevant (see §10) · disclosure `How this works` expanding to the route details and credits (e.g. `Live plays in your browser come from the Jingle Companion.`, `Phone plays come from your Last.fm account. Powered by AudioScrobbler.`, `Some data from ListenBrainz (MetaBrainz Foundation).`) · actions `Manage` (opens Connect sheet at its settings step) and `Disconnect` (ghost danger text; confirms: `Disconnect Apple Music? Your past plays stay unless you delete them.`).
- **Footer of the Connections page:** `Credits` block (always visible there): the required third-party credits (Last.fm AudioScrobbler credit, ListenBrainz/MetaBrainz, Spotify attribution statement, Cover Art Archive/MusicBrainz).
- **A11y:** disclosure is a `<details>`/button with `aria-expanded`.

### 4.31 Additional small components (used by screens)

- **SegmentedControl** (`Circles · Blends` on mobile, `Received · Sent` in Inbox): radiogroup, 40 px, selected segment `--surface-3` with slide indicator.
- **StatusChips for sends:** `Sent` → `Delivered` → `Viewed` → `Played`, rendered as a 4-step chip track; reached steps use `--text` on `--surface-3` with a check; the current step is gradient-outlined; `Played` gets a small Blip `cheer` 16 the first time it appears.
- **Stepper** (onboarding): 4 dots + labels `Profile`, `Sources`, `Privacy`, `Friends`; `aria-current="step"`.
- **InviteLink** (Friends, Circle): read-only field with the URL, `Copy link` button (toast `Link copied`), `Show QR code` (Dialog with QR 240 px on white quiet zone in both themes, caption `Scan to add {me} on Jingle`), expiry note for circle links `Expires in 7 days`.
- **PrivateModeControl:** menu with `1 hour`, `8 hours`, `Until I turn it off`, and `Turn off`.
- **AmbientHeader:** see §5 detail pages and `ambient.shift` motion.

---

## 5. Screens

Format for every screen: **Purpose · Layout (desktop 1440 / mobile 390) · States (default, loading, empty, error, degraded) with exact copy · Key interactions.** Generic error copy comes from §8.3 when not specified. All screens: both themes, 360–1920 px.

### 5.1 Landing (`/`)

- **Purpose:** explain Jingle in one screen and start sign-up.
- **Desktop:** marketing shell. Header: logo, `Sign in` ghost, `Get started` primary, theme toggle. Hero (two columns 7/5): H1 `See what your friends are playing, on any app.` (Bricolage 64/68), sub `Spotify, Apple Music, YouTube Music, Amazon Music. One feed, honest labels, no switching apps.`, primary `Connect your music`, secondary `Sign in`. Right column: a live-looking stack of three demo FeedCards (static demo data, clearly illustrative: caption mono 12 `Example feed`), one LIVE, one RECENT (`2 h ago on Apple Music`), one TOP. Below: three feature rows (Live now · Circles and battles · Blends that explain themselves), each with Blip in a different pose; footer with Privacy, Terms, Credits links.
- **Mobile:** single column; hero text, CTAs full width (48 px), demo card stack becomes a shelf.
- **States:** default; loading n/a (static, SSG); empty n/a; error: static page never errors (if the session check fails, render signed-out); degraded n/a.
- **Interactions:** `Connect your music` → `/signup`. Signed-in visitors redirect to `/home` server-side.

### 5.2 Sign up / Sign in (`/signup`, `/signin`)

- **Purpose:** account in under a minute; 18+ gate (ADR-0011).
- **Layout:** focus shell, 480 px card centred (mobile: full width, 16 px margins). Title `Create your Jingle account` / `Welcome back`. `Continue with Google` (secondary button with a neutral "G"-free generic icon — text only is acceptable; never Google's logo unless used per Google's own button guidelines via Google Identity Services, which renders its own button), divider `or`, email field, password field (show/hide IconButton; strength hint), **Birth year** select (sign-up only; options current year−13 … current year−100, default empty; label `Birth year`; help `You need to be 18 or over to use Jingle.`), consent checkbox `I agree to the Terms and Privacy Policy` (links), primary `Create account`. Footer link `Already have an account? Sign in`.
- **States:**
  - default as above.
  - loading: primary button loading; fields read-only.
  - empty: n/a.
  - error: inline field errors under each field (`Enter an email like name@example.com`, `Use at least 10 characters`, `Pick your birth year`); under-18: the form is replaced by `Jingle is for people 18 and over for now. Thanks for your interest.` with no retry and no account created; email taken: `There's already an account with this email.` + link `Sign in instead`; wrong password: `That email and password don't match.`; Google button hidden when not configured (no dead button); network: `We couldn't reach Jingle. Check your connection and try again.`
  - degraded: if Google sign-in is unavailable at runtime, show `Google sign-in isn't working right now. Use email instead.` above the email form.
- **Interactions:** Enter submits; errors focus the first invalid field and are linked with `aria-describedby`; Google flow returns and asks for birth year on a one-field step if new.

### 5.3 Onboarding (4 steps)

Focus shell with Stepper (`Profile`, `Sources`, `Privacy`, `Friends`), `Back` ghost and primary `Continue` in a sticky footer (mobile) / card footer (desktop). Progress persists server-side; leaving and returning resumes at the same step. Target: populated feed ≤ 5 min (NFR-A11Y-04).

**Step 1 — Profile (`/onboarding/profile`)**
- Fields: avatar upload (optional; drag-drop or pick; generated Avatar shown until then), display name, username (live availability check, mono hint `jingle.app/u/{username}`), optional college/city (`Helps friends find you. Optional.`), genre picker (chips, pick 3+, used for cold-start taste twins).
- States: loading (field skeletons); error `That username is taken. Try {suggestion}.`; upload error `That image didn't upload. Try a JPG or PNG under 5 MB.`; empty n/a; degraded (availability check down: `We'll check your username when you continue.`).

**Step 2 — Sources (`/onboarding/sources`)**
- Title `Which app do you use most?` Sub `Pick one to start. You can add the others any time.`
- Four ConnectPlatformCards in a 2×2 grid (mobile: stacked): Spotify, Apple Music, YouTube Music, Amazon Music. Picking one marks it "most used" (gradient outline, its button becomes primary `Connect {Platform}`). Other cards stay available with secondary buttons.
- **Connect sheet** (right panel / bottom sheet; the only onboarding surface where route words may appear, and only when unavoidable). Flow per platform, orchestrated server-side (BR-13; the user never picks a route):
  1. `Connect {Platform}` — one-line promise per §10 (`You'll show as Live when you play in your browser, and recent plays from your phone.`).
  2. Platform consent step where one exists (Apple Music authorisation, Spotify authorisation for allowlisted testers) — the platform's own screen.
  3. Browser step (desktop browsers): `Install the Jingle Companion for your browser` + primary `Add to {Chrome|Edge|Firefox}` (opens the store listing in a new tab) + `I've added it` secondary; auto-detected when installed.
  4. `Play any song in {Platform} now.` with a link `Open {Platform} in a new tab` → waiting state `Listening for your first play…` (Blip `idle`, spinner) → success `First play seen ✓` with the track title and artwork, Blip `cheer`, confetti-free.
  5. Collapsed `Other ways to connect` disclosure (e.g. for phone-only listeners): Spotify `Link Spotify to Last.fm in Spotify's settings, then connect Last.fm here`; any platform `Already use ListenBrainz or Last.fm? Connect it instead`; YouTube Music `Import your YouTube history (Google Takeout file)` with upload. Token paste field error copy (SRS JNG-01-02): `That token didn't work — copy it again from ListenBrainz settings`.
- States: default; loading (cards skeleton); empty n/a; error in sheet: `We couldn't connect {Platform}. Try again, or use another way to connect.` + `Try again`; waiting > 2 min: `No play yet. Make sure {Platform} is playing in this browser, then try again.` + `Skip for now` (ghost); degraded (orchestrator down): `Connecting is slow right now. You can skip and connect later in Settings.` `Continue` is enabled after any platform shows `Connected ✓` or via `Skip for now`.

**Step 3 — Privacy (`/onboarding/privacy`)**
- Radio group `Who can see what you're playing?`: `Friends` (default), `Only circles I choose`, `No one for now`. Toggles: `Let people find me in suggestions` (default on, JNG-03-06), `Show my exact play time` (default on; off ⇒ labels read `Recently on {Platform}`). Line: `You can change these any time in Settings → Privacy.`
- States: loading (skeleton), error on save (`Couldn't save your privacy choices. Try again.`), empty/degraded n/a.

**Step 4 — Friends (`/onboarding/friends`)**
- InviteLink with QR, suggestion list (SuggestionCards, up to 20), search field. Primary `Go to my feed`.
- Empty: Blip `wave`, `No suggestions yet.`, `Invite a friend and you'll see them here.`, action `Copy invite link`.
- Loading: 6 SuggestionCard skeletons. Error: `Couldn't load suggestions.` + `Retry`. Degraded: cached suggestions with mono `Updated {n} min ago`.

### 5.4 Home (`/home`)

- **Purpose:** friends' listening at a glance; the habit loop.
- **Desktop order:** HeroCarousel → FilterChips (`All`, `Live`, one per circle) → **Live now** shelf (live variant) → **From your circles** shelf (circle-grouped FeedCards; header mono `{n} circles`) → **Sent to you** shelf (received sends: FeedCard-like SendCard with sender, note preview 1 line, StatusChip `New`) → **Quick send** grid → **People you may know** shelf (SuggestionCards) → **Everyone else** (vertical grid of all remaining friend cards sorted Live → Recent newest first → Top → Hidden, paginated by cursor).
- **Mobile 390:** hero 4:5 → chips row → shelves with 2 + peek cards → quick send 2-col grid → suggestions shelf → feed as 72 px rows.
- **Filter behaviour:** `Live` filters every section to LIVE cards (sections with none hide; if all hide, show the Live empty state). Circle chip scopes Live now, the circle shelf and the feed to that circle's members; hero stays.
- **States:**
  - default above.
  - loading: hero skeleton, chip row with real `All`/`Live` chips + 3 chip skeletons, each shelf title rendered + skeleton cards.
  - empty (no friends): hero hidden; single EmptyState Blip `wave`: title `Your feed is waiting for friends`, body `Add a friend and you'll see what they're playing here.`, action (primary) `Invite friends` (opens InviteLink dialog). Below: People you may know shelf if any suggestions.
  - empty Live now shelf (friends exist, nobody live): shelf stays with a compact inline empty: Blip `sleepy` 48 + `No one's playing right now.` + ghost `Send a song instead` (opens Send sheet).
  - empty with Live filter selected: `No one's live right now.` + ghost `Show everyone` (selects `All`).
  - Sent to you empty: shelf hidden. Quick send empty: see §4.21.
  - error (feed request fails): ErrorState `We couldn't load your feed.` body `This is on us. Try again in a moment.` + `Try again`. Individual shelf failures use the inline shelf error.
  - degraded (`degraded: true` on cards or realtime down): cards show honest labels + `delayed` tag; a single mono line under the chips `Some friends' plays may be delayed. Showing the latest we have.` (no route names). Realtime disconnected: AppShell `Reconnecting…` banner; cards keep last state; LIVE badges drop to RECENT when the server says so (client never keeps Live past 90 s since `observed_at`; client-side guard demotes to label-less state until next update).
- **Key interactions:** Live cards update in place (`feed:update`); new Live friends enter the front of Live now; polite announcement throttled (§9.4). Card → Track detail sheet (artwork, title, artist, friend line, label, actions `Open in {my platform}`, `Send`, `React`, `Start a Blend with {name}`). Not on my platform: `Not found on {Platform}` + `Search in {Platform}`.

### 5.5 Send sheet (global; from any card, NowPlayingBar, quick send)

- Layout: track header (Artwork 64, title, artist) · recipient picker (search, chips for selected people/circles, recent recipients row) · optional note textarea (max 280, counter mono `{n}/280`) · `Add more songs to make a mixtape` (expands to a 5–8 track list with search) · primary `Send`.
- States: sending (optimistic: sheet closes immediately, toast `Sent to {name}` / `Sent to {n} people` with Blip `cheer`); failure (toast persistent `Couldn't send to {name}. Try again.` + `Retry`, the Inbox item shows `Not sent`); mixtape with < 5 tracks: Send disabled with hint `Add at least 5 songs, or remove extras to send one song`; note over limit: counter turns `--danger-text`, Send disabled; empty recipients: Send disabled, hint `Pick at least one friend or circle`.

### 5.6 Friends (`/friends`)

- **Purpose:** requests, suggestions, search, invite.
- **Desktop:** H1 `Friends` + InviteLink card on the right (link, `Copy link`, `Show QR code`). Tabs `Requests ({n})`, `Suggestions`, `Find people`, `Your friends ({n})`. Requests: two lists `Received` (Avatar 40, name, mutuals mono, `Accept` secondary + `Decline` ghost; the one primary on this view is the invite CTA) and `Sent` (`Cancel`). Suggestions: grid of SuggestionCards. Find: search field + results rows (`Add`, `Requested`, `Friends`). Your friends: rows with Avatar, name, current FeedCard label, `More` (`Remove friend`, `Block`, `Report`).
- **Mobile:** InviteLink becomes a banner card at top; tabs scroll horizontally.
- **States:**
  - loading: row/card skeletons per tab.
  - empty Requests: Blip `sleepy`, `No requests right now.`, action `Share your invite link`. Empty Suggestions (JNG-03-07 starter): Blip `wave`, `No suggestions yet.`, `As you and your friends listen, we'll find people you'd get along with.`, action `Share your invite link`; plus starter content if the server provides it (taste twins, public circles near your college). Empty Find (no query): `Search by name or username.`; no results `No one called "{q}". Check the spelling or share your invite link.` Empty Your friends: Blip `wave`, `No friends yet`, action `Invite friends`.
  - error: `Couldn't load {tab}.` + `Retry`. Request actions fail: toast `Couldn't {accept|decline|send} that request. Try again.`
  - degraded: suggestions from cache with `Updated {n} h ago`.
- **Interactions:** Accept/Decline optimistic with undo toast (`Request declined · Undo`, 6 s). Remove and Block use Dialog confirm: `Remove {name}?` body `They'll stop seeing your activity right away. They won't be told.` / `Block {name}?` body `You won't see each other anywhere on Jingle. They won't be told.` (danger button `Block`). Invite link opens `/invite/{code}` which auto-sends a request after sign-in (JNG-02-07).

### 5.7 Circles list (`/circles`) and Circle page (`/circles/{id}`)

**Circles list**
- Desktop: H1 `Circles` + primary `Create a circle`; section `Suggested for you` (suggested CircleCards, if any); section `Invites` (invite CircleCards); section `Your circles` grid. Mobile: SegmentedControl `Circles · Blends` under the title; same sections stacked.
- States: loading (card grid skeleton); empty: Blip `wave`, `Circles are small groups for your people.`, body `Make one for your flatmates, your band or your college crew.`, action `Create a circle`; error `Couldn't load your circles.` + Retry; degraded: cached list, mono `Updated {n} min ago`; limit reached (20 circles): Create disabled with hint `You're in 20 circles, the most allowed. Leave one to create another.`
- Create dialog: name (max 40), cover (upload or generated), visibility (`Private (invite only)` default / `Discoverable at my college`), invite friends picker. Primary `Create circle`.

**Circle page**
- **Ambient header** (340 px desktop / 240 mobile): background = blurred (60 px) circle cover scaled 120%, colour wash from `useArtworkColor(cover)` at 40% under a theme scrim (`--ambient-scrim`, §7); translucent TopBar over it. Content: cover 160 (mobile 96), eyebrow mono `CIRCLE · {n} MEMBERS`, name Bricolage 56 (mobile 32), AvatarStack, actions: `Start session` (primary), `Invite` (secondary), `More` (`Settings` for admins, `Leave circle`, `Report`).
- **Body sections:** Live shelf (`Live in {circle}`) → Battle panel (current phase: `Nominate by Fri 18:00` with Nominate button / `Vote: 3 left` / `Results Sunday 21:00` countdown / podium link) → Circle Blend (row of top 5 BlendTrackRows + `Open Blend`; if none `Make a circle Blend` secondary) → Circle feed (FeedCards grid, members only) → Members (list with role tags `Owner`, `Admin`; admin actions in `More`).
- **Mobile:** sections stack; Battle panel becomes a card right after the header.
- **States:** loading (header skeleton keeps 340 px height, sections skeleton); empty (only you in the circle): Blip `wave`, `It's quiet in here.`, `Invite people to start the feed and this week's battle.`, action `Invite to circle`; error: not a member or deleted `This circle isn't available.` + `Back to circles`; generic `Couldn't load this circle.` + Retry; degraded: cached feed + delayed tags; full circle on invite link: `This circle is full` (JNG-04-01), no join button.
- **Interactions:** ambient colour cross-fades when the cover changes; Invite dialog has friend picker + InviteLink (`Expires in 7 days`); Leave confirm `Leave {circle}? You can rejoin with a new invite.`; owner must transfer first: `Hand over ownership before you leave.`

### 5.8 Blends list (`/blends`) and Blend detail (`/blends/{id}`)

**Blends list:** H1 `Blends` + primary `New Blend`. Grid of Blend cards (GenerativeCover seeded by Blend id with member avatars overlapping bottom-left, name `Aanya + Dev + you`, mono `30 songs · updated {n} d ago`). New Blend dialog: pick 2–6 friends or a circle; primary `Make Blend`; generating state with Blip `idle` `Mixing your Blend…`.
- States: loading grid skeleton; empty Blip `wave`, `Blends mix your taste with friends'.`, `Pick up to 5 friends and we'll find songs you'll all like.`, action `Make a Blend`; error `Couldn't load your Blends.` + Retry; degraded cached.

**Blend detail**
- Ambient header from the top track artwork: eyebrow `BLEND`, title, AvatarStack of members, mono `30 songs · {n}% you · {m}% Aanya …` (balance, never > 40% per member shown honestly), actions `Save to {my platform}` (primary where the API allows; else hidden with note under header `Saving to {Platform} isn't available yet. Open songs one by one.`), `Regenerate` (secondary; keeps pinned), `More` (`Rename`, `Leave Blend`).
- Body: `<ol>` of 30 BlendTrackRows, each with a reason line.
- States: loading (header + 10 row skeletons); empty (not enough shared data): Blip `sleepy`, `Not enough listening to blend yet.`, `Give it a few days of listening and try again.`, action `Remind me` (secondary) — the one action; error `Couldn't load this Blend.` + Retry; generating (on regenerate: non-pinned rows skeleton, toast `Fresh Blend ready` on finish); save failed `Couldn't save to {Platform}. Try again.`; degraded: cached tracks + header mono `Updated {n} h ago`.

### 5.9 Live session (`/sessions/{id}`)

- **Purpose:** shared queue with votes; everyone plays on their own app.
- **Desktop:** two columns 8/4. Left: session header (name Bricolage 32, host Avatar + `Hosted by {name}`, participant AvatarStack, `{n} here` mono), Now card (large, Artwork 200, `Open in {my platform}` primary), Queue (`<ol>` of SessionQueueRows), `Add a song` search field (toggle `Add anonymously`). Right: Participants list and short chat (Should; if not built, hidden). NowPlayingBar switches to session strip.
- **Mobile:** header compact; Now card; tabs `Queue · People`; `Add a song` as a floating secondary button bottom-right above the mini-bar, opens search sheet.
- **States:** loading (header + Now + 5 row skeletons); empty queue: Blip `wave`, `The queue is empty.`, `Add the first song.`, action `Add a song`; reconnecting (JNG-07-09): top banner `Reconnecting… your votes are saved.`, queue dims to 70% and votes are queued locally; on reconnect `Back in sync` toast and the queue snaps to server state (rows animate to new order); error joining: `This session has ended.` + `Back to {circle}` or `You're not invited to this session.`; host left (JNG-07-08): toast `{old} left. {new} is now the host.`; ended: `Session ended · {n} songs played` summary with Blip `cheer`; degraded (realtime slow): banner `Updates are slow right now. Your votes still count.`
- **Interactions:** votes optimistic with `Idempotency-Key`; ranking animates within 1 s; `Open in my app` on each row.

### 5.10 Rituals (`/rituals`, battle, recap)

**Rituals hub:** H1 `Rituals`. Section `This week's battles`: one card per circle with phase, countdown (mono), and the single relevant action (`Nominate`, `Vote`, `See results`). Section `Your recap`: RecapFlipCard preview (front face) + `Open recap`. Section `Season` (per circle season table link).
- States: loading skeleton; empty (no circles): Blip `wave`, `Battles happen inside circles.`, `Join or create a circle to play this week.`, action `Create a circle`; error; degraded cached with mono update time.

**Battle (`/rituals/battles/{id}`)** — phases (times in viewer's local zone, source times IST per PRD 5.9):
1. *Nominate* (Mon 18:00 → Fri 18:00): header `Nominate one song`, song search across platforms (results show PlatformBadge-free canonical titles), your nomination card with `Change`; count mono `{n} of {m} members nominated`. Rule copy: `One song each. You can change it until Friday 18:00.`
2. *Vote* (Fri 18:00 → Sun 21:00): grid of nominated songs (anonymised nominator until reveal), each with `Vote` toggle; counter `3 votes left` → `All votes used`; own nomination shows `Your song` and no vote button (JNG-09-02).
3. *Results pending* (Sun 21:00 → +5 min): `Counting votes…` Blip `idle`.
4. *Revealed:* BattlePodium + leaderboard + `Season table`.
- States: loading; empty no nominations: Blip `sleepy`, `No songs nominated yet.`, action `Nominate a song`; late vote error (Gherkin): toast `Voting has closed` and UI flips to phase 3; admin skipped week: `This week is off. Back next Monday.` with Blip `sleepy`; error `Couldn't load this battle.` + Retry; degraded: cached counts with `Updated {n} min ago`, voting still allowed (server validates).

**Recap (`/rituals/recap/{yyyy-mm}`):** centred RecapFlipCard; month switcher (‹ Sept 2026 ›); `Share` primary, `Download image`. States: not ready `Your {Month} recap arrives by the 2nd.` (Blip `sleepy`, action `See last month`); not enough data `Not enough listening in {Month} for a recap.` action `Connect your music`; loading/generating; error `Couldn't make your recap. Try again.`; degraded n/a (recap is a snapshot).

### 5.11 Profile (`/u/{username}`)

- **Ambient header** from the person's current or top artwork: Avatar 128 (mobile 96), name Bricolage 56/32, `@username` mono, their current FeedCard label (e.g. `Live on Spotify` with LiveBadge if LIVE), PlatformBadges of platforms used, actions: friend → `Send a song` (primary), `Start a Blend`, `More` (`Remove friend`, `Block`, `Report`); own → `Edit profile` (secondary), Settings gear; stranger → `Add friend` (primary).
- **Body (friend):** CompatibilityMeter with breakdown → Shared artists shelf → Their top this month (artwork grid 5) → Taste timeline (12-month stacked area chart of genre shares; own only, or overlay with consent later) → Recent plays list (respecting privacy).
- **Body (own):** Stats (minutes, top artists, genres, platforms used as text badges with %) → Taste timeline → Recap entry.
- **States:** loading (header height preserved, meter + list skeletons); empty analytics (JNG-08-06): Blip `sleepy`, `Your stats are warming up.`, `They build over 2–4 weeks of listening.`, action `Connect another app`; limited shared data (friend has privacy on): `{name} keeps their listening private.` no numbers; stranger: `Add {name} as a friend to see what they play.`; error `Couldn't load this profile.` + Retry; blocked/not found: `This profile isn't available.`; degraded: cached stats `Updated {n} h ago`.

### 5.12 Inbox of sends (`/inbox`)

- **Purpose:** received recommendations (JNG-06-07) and delivery status of what I sent (JNG-06-04).
- Layout: H1 `Inbox`; SegmentedControl `Received · Sent`. Received rows: sender Avatar, track/mixtape artwork, title, note (2 lines, expandable), time mono, `Open in {my platform}` (secondary; this view has no primary button), `React`, `Reply with a song`. New rows have a gradient 6 px dot. Sent rows: track, recipients, StatusChips `Sent` `Delivered` `Viewed` `Played` per recipient (expand for per-person status), discovery credit tag `Discovery credit` when earned.
- **States:** loading 6 row skeletons; empty Received: Blip `wave`, `Nothing here yet.`, `When friends send you songs, they land here.`, action `Send a song first`; empty Sent: Blip `sleepy`, `You haven't sent anything yet.`, action `Send a song`; error `Couldn't load your inbox.` + Retry; not on my platform: row shows `Not found on {Platform}` + `Search in {Platform}`; degraded: statuses may lag, mono `Status updated {n} min ago`.
- **Interactions:** status chips update live via `notify`; viewing a received row marks it Viewed.

### 5.13 Notifications (popover + `/notifications`)

- Popover 400 × max 560 from the bell; list of rows (icon/avatar, text, time mono), `Mark all as read`, `See all`. Types: friend request, request accepted, send received, send played, battle phase, battle results, recap ready, circle invite, session started. Copy never names routes (e.g. `Aanya is live on Apple Music` never appears as push more than once a day; in-app row `Aanya started a session in Indie night crew`).
- States: loading skeleton rows; empty Blip `cheer` 64, `You're all caught up.` (no action needed — the one action is `Notification settings` ghost); error `Couldn't load notifications.` + Retry.

### 5.14 Settings (`/settings/*`)

Layout: desktop sub-nav left (200 px) `Connections`, `Privacy`, `Notifications`, `Accessibility`, `Data`; mobile list → detail pages.

**Connections** — H2 `Your music apps`. SettingsConnectionsRows for Spotify, Apple Music, YouTube Music, Amazon Music (+ `Add another app` opening the onboarding Connect sheet). Honest capability notes (§10), e.g. `Phone listening on Apple Music shows as recent plays, not live.` Credits block at the bottom. States: loading row skeletons; empty (no sources) Blip `wave`, `No music apps connected.`, action `Connect your music`; error `Couldn't load your connections.` + Retry; needs re-consent (JNG-01-11): row status `Needs reconnect` + warning text and `Reconnect {Platform}` button, plus an in-app notification; degraded: row status `Delayed` with `Plays from {Platform} are arriving late. We're on it.` (no route words outside the `How this works` disclosure).

**Privacy** — `Who can see what you're playing` (Friends / Only circles I choose / No one), **Private mode** (PrivateModeControl: `Hide my activity for 1 hour`, `8 hours`, `Until I turn it off`; while on, banner `Private mode is on until {HH:mm}. Friends see "Hidden".`), `Show my exact play time`, `Let people find me in suggestions`, `Blocked people` list with `Unblock`. Saves instantly with toast `Saved`; failure reverts toggle with toast `Couldn't save. Try again.`

**Notifications** — per-type toggles (in-app always on; push per type), `Allow browser notifications` (only after a user click, never on load), daily push limit (default 5), quiet hours (default 23:00–08:00), `One "friends are live" push a day at most` note.

**Accessibility** — `Theme` (Dark / Light / Match system), `Reduce motion` (Match system / On / Off; On forces reduced-motion behaviour), `Announce when friends go live` (screen reader announcements on/off, default on).

**Data** — `Download my data` (primary: `Request export`; state `Preparing your file… we'll notify you` → `Download (JSON, {size})`, link valid 7 days), `Delete my account` (danger; Dialog requires typing username; copy `This deletes your account, plays, sends and circles you own. It can't be undone.`; primary danger `Delete my account`). Per-source unlink lives in Connections (JNG-01-09).

### 5.15 `/design` route

- Purpose: living reference. Sections in order: Tokens (colour swatches with the contrast table from §7 rendered live and computed in-page), Type scale, Spacing/radius/elevation, Motion (each §6 entry with a replay button and a reduced-motion toggle), Every §4 component in every variant and state, FeedCard matrix (LIVE, RECENT ×4 platforms, TOP, HIDDEN, Degraded, Unresolved, attribution SPOTIFY) at shelf and row sizes, Blip poses, Empty/Error/Degraded examples per screen, Breakpoint preview frames (360/390/768/1024/1440/1920 iframes).
- Theme toggle top-right plus `Side by side` switch showing dark and light columns. Screenshots for design review are taken from here.

---

## 6. Motion catalogue

Library: `motion` (`motion/react`). Presets in `apps/web/src/lib/motion.ts`. Only `transform` and `opacity` (and `filter` on the ambient background layer, which is its own composited layer) are animated. Every entry reads `useReducedMotion()` or the Settings → Accessibility override. Budget: 60 fps on a mid-range laptop at 1440 px; no animation triggers layout of other elements (use `layout` only inside fixed-size containers such as lists).

Spring presets: `spring.soft` = stiffness 260, damping 30, mass 1. `spring.snappy` = 400, 32, 1. `spring.bouncy` = 320, 18, 1 (celebrations only). `spring.gentle` = 170, 26, 1 (large surfaces). Easings: `ease.standard` = cubic-bezier(0.2, 0, 0, 1); `ease.exit` = cubic-bezier(0.3, 0, 1, 1); `ease.linear`.

| Name | Trigger | Property | Spring / duration + easing | Reduced-motion fallback |
| --- | --- | --- | --- | --- |
| `card.enter` | Card mounts in a shelf/grid (first load, pagination, new Live) | opacity 0→1, y 12→0, scale 0.98→1 | `spring.soft`, stagger 40 ms, max 8 staggered (rest instant) | opacity 0→1, 120 ms linear, no stagger |
| `card.exit` | Card removed (dismiss suggestion, filter change) | opacity 1→0, scale 1→0.96 | 160 ms `ease.exit` | opacity 1→0, 100 ms |
| `card.reorder` | List order changes (Live first, queue votes) | transform via `layout` | `spring.soft` | instant jump; focus preserved |
| `card.toDetail` | Card click → Track detail / Circle / Blend page | shared `layoutId="card-{id}"` on artwork (transform) | `spring.gentle` | cross-fade 150 ms |
| `card.hover` | Pointer hover on card | artwork scale 1→1.03, action cluster opacity 0→1, y 4→0 | `spring.snappy` | action cluster opacity only, 0 ms |
| `press` | Pointer down on Button/IconButton/Chip/card | scale 1→0.97 (chips 0.96) | `spring.snappy` | none (colour change only) |
| `focus.ring` | Focus-visible | ring opacity 0→1 | 80 ms linear | same (not motion) |
| `chip.select` | Chip selected | background opacity, check icon scale 0.6→1 | `spring.snappy` | instant |
| `tab.underline` | Tab change | underline x/width via `layoutId` | `spring.snappy` | instant |
| `live.equaliser` | Card state LIVE & visible | bar scaleY 0.25↔1 | 0.9/1.3/1.1/1.0 s `ease-in-out` infinite alternate | static bars |
| `live.ring.pulse` | Card becomes LIVE | coral ring opacity 0→1 then one 1.4× scale-out ghost ring fading | 600 ms `ease.standard`, once | ring appears instantly, no ghost |
| `label.crossfade` | freshness_label changes | old opacity 1→0 / new 0→1 (stacked, fixed width box) | 180 ms `ease.standard` | instant swap |
| `shelf.scroll` | Arrow button | `scrollBy({behavior:"smooth"})` | browser smooth | `behavior:"auto"` |
| `hero.slide` | Carousel advance | x translate of track | `spring.gentle`; autoplay 7 s | no autoplay; instant |
| `sheet.enter` / `exit` | Sheet/Dialog open/close | y 100%→0 (mobile), x 100%→0 (side panel), dialog scale 0.96→1 + opacity; scrim opacity 0→0.6 | enter `spring.gentle`; exit 180 ms `ease.exit` | opacity 150 ms |
| `toast.enter` | Toast shown | y 16→0, opacity | `spring.snappy`; exit 150 ms | opacity |
| `skeleton.shimmer` | Skeleton visible | shine translateX −100%→100% | 1.4 s linear infinite | static |
| `optimistic.send` | Send pressed | paper-plane icon x 0→24, y 0→−12, opacity 1→0; toast | 350 ms `ease.standard` | toast only |
| `optimistic.vote` | Vote pressed | icon scale 1→1.25→1, score number y roll (old up/out, new in) | `spring.bouncy` | instant number change |
| `podium.reveal` | Battle revealed (first view, or Replay) | blocks scaleY 0→1 (origin bottom) 3rd → 2nd → 1st at 0 / 500 / 1100 ms; artwork y 20→0 + opacity; confetti dots translate + opacity 1.2 s | blocks `spring.bouncy`; artwork `spring.soft` | final state instantly; no confetti |
| `recap.flip` | Next face | rotateY 0→180° with `perspective: 1200px`, backface hidden | `spring.gentle` (≈ 500 ms) | cross-fade 150 ms |
| `ambient.shift` | Artwork of header changes / page enters | background layer opacity cross-fade between two stacked gradient layers; blurred art scale 1.2→1.15 slow drift | 800 ms `ease.standard`; drift 20 s alternate | cross-fade 0 ms (instant), no drift |
| `blip.idle` | Blip mounted in idle/empty | scale 1↔1.03 | 3.2 s `ease-in-out` infinite | static |
| `blip.pose` | Blip mounts in wave/cheer | arm rotate / body y hop | `spring.bouncy`, once | static pose |
| `connect.firstPlay` | First play seen | check icon path draw (stroke-dashoffset via transform-free SVG) + Blip cheer | 400 ms `ease.standard` | check shown instantly |
| `highlight.deeplink` | Deep-link target | outline opacity pulse ×2 | 1.2 s | static outline 2 s |

Rules: no motion longer than 800 ms blocks interaction; nothing autoplays over 5 s except the equaliser, Blip idle, ambient drift and hero autoplay (all pausable/stoppable and off under reduced motion; WCAG 2.2.2); nothing flashes more than 3 times per second.

---

## 7. Colour, typography and spacing tokens

Names are CSS variables in `packages/design-tokens/src/tokens.css`; dark is the default on `:root`, light is `[data-theme="light"]`. `Match system` sets the attribute from `prefers-color-scheme`. The theme script runs before paint (no flash).

### 7.1 Colour tokens

| Token | Dark | Light | Use |
| --- | --- | --- | --- |
| `--brand-violet` | #8B6BFF | #8B6BFF | gradient start |
| `--brand-cyan` | #3FE7D8 | #3FE7D8 | gradient end |
| `--gradient-brand` | linear-gradient(135deg, #8B6BFF, #3FE7D8) | same | primary button, selected chip, focus ring (dark), active indicators |
| `--on-brand` | #0B0B12 | #0B0B12 | text/icons on gradient |
| `--accent-text` | #A68CFF | #5B3FD9 | links and brand-coloured text (gradient text is not allowed) |
| `--bg` | #08080B | #F7F7FA | page |
| `--surface-1` | #121217 | #FFFFFF | cards, sidebar, sheets |
| `--surface-2` | #1A1A21 | #F0F0F5 | hover, chips, inputs |
| `--surface-3` | #24242D | #E6E6EE | selected, badges |
| `--surface-glass` | rgba(18,18,23,0.72) | rgba(255,255,255,0.72) | TopBar glass (with 20 px blur) |
| `--border` | #2E2E38 | #E0E0E8 | hairlines (decorative) |
| `--border-strong` | #6E6E80 | #7C7C90 | input borders, focus-independent control boundaries (≥ 3:1) |
| `--text` | #F4F4F7 | #111118 | primary text |
| `--text-muted` | #A3A3B2 | #55556A | secondary text, mono labels |
| `--live` | #FF6B5E | #FF6B5E | Live pill fill, Live ring, Live dot, equaliser (Live only) |
| `--on-live` | #1A0705 | #1A0705 | text/bars on the Live pill |
| `--live-text` | #FF6B5E | #B8401F | Live label text (Live only) |
| `--danger-text` | #FB7185 | #BE123C | error text, destructive links |
| `--danger-bg` | #FB7185 | #BE123C | danger button fill |
| `--on-danger` | #1A0508 | #FFFFFF | text on danger button |
| `--warning-text` | #F5B84A | #8A5300 | `delayed` tag text, needs-attention |
| `--warning-bg` | rgba(245,184,74,0.14) | rgba(138,83,0,0.10) | `delayed` pill |
| `--success-text` | #4ADE80 | #15803D | connected, success |
| `--focus-ring` | 2 px outline, gradient #8B6BFF→#3FE7D8 | 2 px outline, gradient #5B3FD9→#0E7C74 | focus-visible (≥ 3:1 against adjacent colours) |
| `--skeleton` / `--skeleton-shine` | #1A1A21 / rgba(255,255,255,0.06) | #E6E6EE / rgba(255,255,255,0.7) | skeletons |
| `--scrim` | rgba(0,0,0,0.60) | rgba(17,17,24,0.40) | dialogs |
| `--ambient-scrim` | linear-gradient(to bottom, rgba(8,8,11,0.55) 0%, rgba(8,8,11,0.80) 60%, #08080B 100%) | linear-gradient(to bottom, rgba(247,247,250,0.60) 0%, rgba(247,247,250,0.86) 60%, #F7F7FA 100%) | over blurred art on detail headers |
| `--text-on-ambient` / `--text-on-ambient-muted` | #F4F4F7 / #C9C9D6 | #111118 / #4A4A5C | header text over ambient art |

Ambient colour: `useArtworkColor(url)` extracts a dominant colour, then clamps it to HSL lightness 30–45% (dark) or 70–85% (light) and saturation ≤ 60% before use as the wash. Text never sits directly on raw artwork colour; the scrim guarantees the ratios below. Coral-like hues (0–20°) extracted from art are allowed in the wash only at ≤ 30% saturation so a red cover never reads as Live.

### 7.2 Contrast ratios (WCAG 2.x relative luminance, computed for this spec)

| Foreground | Background | Theme | Ratio | Passes |
| --- | --- | --- | --- | --- |
| `--text` #F4F4F7 | `--bg` #08080B | dark | 18.22 | AA/AAA |
| `--text` #F4F4F7 | `--surface-1` #121217 | dark | 17.01 | AA |
| `--text` #F4F4F7 | `--surface-2` #1A1A21 | dark | 15.76 | AA |
| `--text` #F4F4F7 | `--surface-3` #24242D | dark | 14.01 | AA |
| `--text-muted` #A3A3B2 | `--bg` | dark | 8.04 | AA |
| `--text-muted` #A3A3B2 | `--surface-1` | dark | 7.50 | AA |
| `--text-muted` #A3A3B2 | `--surface-2` | dark | 6.95 | AA |
| `--text-muted` #A3A3B2 | `--surface-3` | dark | 6.18 | AA |
| `--accent-text` #A68CFF | `--surface-1` | dark | 6.95 | AA |
| `--on-brand` #0B0B12 | #8B6BFF (gradient violet end, worst case) | both | 5.27 | AA |
| `--on-brand` #0B0B12 | #3FE7D8 (gradient cyan end) | both | 12.73 | AA |
| `--on-live` #1A0705 | `--live` #FF6B5E | both | 6.98 | AA |
| `--live-text` #FF6B5E | `--surface-1` | dark | 6.68 | AA |
| `--live-text` #FF6B5E | `--bg` | dark | 7.16 | AA |
| `--danger-text` #FB7185 | `--surface-1` | dark | 6.94 | AA |
| `--warning-text` #F5B84A | `--surface-1` | dark | 10.53 | AA |
| `--success-text` #4ADE80 | `--surface-1` | dark | 10.72 | AA |
| `--text-on-ambient-muted` #C9C9D6 | worst-case scrimmed header (#3A3A3D, white art under 80% scrim) | dark | 6.91 | AA |
| `--text-on-ambient` #F4F4F7 | #3A3A3D | dark | 10.33 | AA |
| `--border-strong` #6E6E80 | `--surface-1` | dark | 3.74 | 1.4.11 (≥ 3:1) |
| focus ring violet #8B6BFF | `--bg` | dark | 5.38 | 1.4.11 |
| `--text` #111118 | `--bg` #F7F7FA | light | 17.58 | AA |
| `--text` #111118 | `--surface-1` #FFFFFF | light | 18.80 | AA |
| `--text` #111118 | `--surface-2` #F0F0F5 | light | 16.55 | AA |
| `--text` #111118 | `--surface-3` #E6E6EE | light | 15.14 | AA |
| `--text-muted` #55556A | `--bg` | light | 6.79 | AA |
| `--text-muted` #55556A | `--surface-1` | light | 7.26 | AA |
| `--text-muted` #55556A | `--surface-2` | light | 6.39 | AA |
| `--text-muted` #55556A | `--surface-3` | light | 5.85 | AA |
| `--accent-text` #5B3FD9 | `--surface-1` | light | 6.65 | AA |
| `--accent-text` #5B3FD9 | `--surface-2` | light | 5.85 | AA |
| `--live-text` #B8401F | `--surface-1` | light | 5.54 | AA |
| `--live-text` #B8401F | `--surface-2` | light | 4.88 | AA |
| `--danger-text` #BE123C | `--surface-1` | light | 6.29 | AA |
| `--warning-text` #8A5300 | `--surface-2` | light | 5.57 | AA |
| `--success-text` #15803D | `--surface-1` | light | 5.02 | AA |
| `--text-on-ambient-muted` #4A4A5C | worst-case scrimmed header (#D5D5D8, black art under 86% scrim) | light | 5.91 | AA |
| `--border-strong` #7C7C90 | `--surface-1` | light | 4.08 | 1.4.11 |
| focus ring #5B3FD9 / #0E7C74 | `--bg` | light | 6.22 / 4.73 | 1.4.11 |

Known failing pairs, therefore **banned**: coral #FF6B5E as text on light surfaces (2.79), violet #8B6BFF as text on light (3.48), white text on violet (3.39; hence dark `--on-brand`), any text on raw gradient midpoints with white. Disabled controls (40% opacity) are exempt under 1.4.3 but must still be identifiable by shape.

### 7.3 Typography

Loaded via `next/font/google` with `display: swap` and size-adjusted fallbacks (no layout shift). Numerals in data use `font-variant-numeric: tabular-nums`.

| Token | Font | Desktop size/line | Mobile size/line | Weight | Use |
| --- | --- | --- | --- | --- | --- |
| `display-xl` | Bricolage Grotesque | 64/68, −2% tracking | 40/44 | 700 | Landing hero, recap numbers |
| `display-l` | Bricolage Grotesque | 56/60 | 32/36 | 700 | Detail page titles (Profile, Circle, Blend) |
| `display-m` | Bricolage Grotesque | 40/44 | 28/32 | 700 | Hero carousel titles |
| `display-s` | Bricolage Grotesque | 28/32 | 22/28 | 600 | Page H1 on dense pages |
| `section` | Bricolage Grotesque | 22/28 | 20/26 | 600 | Shelf titles |
| `title-l` | Inter | 20/28 | 20/28 | 600 | Dialog titles |
| `title-m` | Inter | 16/22 | 16/22 | 600 | Card names, row titles |
| `body` | Inter | 15/22 | 16/24 | 400 | Body text (16 on mobile; inputs always 16 to avoid zoom) |
| `body-s` | Inter | 13/18 | 13/18 | 400/500 | Secondary text, reasons |
| `label` | Inter | 11/14, +6% tracking, uppercase | same | 700 | LIVE pill, eyebrows alternative |
| `mono-m` | JetBrains Mono | 14/20 | 14/20 | 500 | scores, counts |
| `mono-s` | JetBrains Mono | 12/16 | 12/16 | 500 | freshness labels, timestamps, eyebrows |

Text scales with the user's browser font size (rem units); layouts tolerate 200% zoom and 1.4.12 text spacing without clipping (titles wrap to 2 lines, then ellipsis with full text in the accessible name).

### 7.4 Spacing, radius, elevation, z-index

- Spacing (4 px grid): `--space-1` 4, `-2` 8, `-3` 12, `-4` 16, `-5` 20, `-6` 24, `-8` 32, `-10` 40, `-12` 48, `-16` 64.
- Radius: `--r-sm` 8, `--r-md` 12, `--r-lg` 20, `--r-pill` 999.
- Elevation: dark relies on surface steps + `--border`; shadows `--shadow-1` 0 1px 2px rgba(0,0,0,.4), `--shadow-2` 0 8px 24px rgba(0,0,0,.5). Light: `--shadow-1` 0 1px 2px rgba(17,17,24,.08), `--shadow-2` 0 8px 24px rgba(17,17,24,.12).
- Z-index: base 0, sticky 10, sidebar 20, topbar 30, nowplaying 40, tabbar 41, popover 50, sheet 60, dialog 70, toast 80, skip-link 90.
- Durations: `--dur-fast` 120 ms, `--dur-base` 200 ms, `--dur-slow` 320 ms.

---

## 8. Copy guide

### 8.1 Tone

Warm, short, plain. Talk like a friend who knows music, not a system. Sentence case everywhere (buttons included). Second person ("you"), contractions welcome. No exclamation marks except in success moments with Blip (max one). No jargon: never "sync", "ingest", "token", "API", "route", "scrobble" in product UI (exceptions: §1 principle 8). Numbers as digits. Times in the viewer's locale; 24-hour clock in India locale default.

### 8.2 Freshness label grammar (exactly CONTRACTS.md §7)

The server sends `freshness_label`; the client renders it verbatim and never builds or edits it.

- `Live on {Platform}`
- `{n} min ago on {Platform}`
- `{n} h ago on {Platform}`
- `{n} d ago on {Platform}`
- `Top this month`
- `Hidden`
- Platform display names: `Spotify`, `Apple Music`, `Amazon Music`, `YouTube Music`. `UNKNOWN` ⇒ omit ` on …` (e.g. `20 min ago`).
- When the friend hides precise time, `observed_at` is omitted and the label reads e.g. `Recently on Spotify`.
- Degraded: the `delayed` tag is a separate visual element driven by `degraded: true`, rendered after the label as ` · delayed`; it is not part of the label string.
- Never append a route (`via …`) — ADR-0002.

### 8.3 Error copy

Pattern: what happened (plain) + what to do. Never blame, never show codes except the mono `Ref {request_id}` line.

| Situation / API code | Copy |
| --- | --- |
| Network offline | `You're offline. Showing what we had at {HH:mm}.` |
| 5xx / unknown | `Something went wrong on our side. Try again in a moment.` |
| Timeout | `That took too long. Try again.` |
| 401 session expired | `You've been signed out. Sign in again to continue.` |
| 403 not allowed | `You don't have access to this.` |
| 404 | `This isn't available. It may have been removed.` |
| 409 duplicate request | `You're already friends.` / `Request already sent.` |
| 429 rate limit (30 requests/day) | `You've sent a lot of requests today. Try again tomorrow.` |
| Battle vote late | `Voting has closed` |
| Circle full | `This circle is full` |
| Track not on my platform | `Not found on {Platform}` + `Search in {Platform}` |
| Compatibility sound data missing | `Sound comparison unavailable` |
| Source needs re-consent | `Your {Platform} connection expired. Reconnect to keep your plays up to date.` |
| Upload invalid | `That file didn't work. Upload the watch-history.json from your Google Takeout.` (Connect sheet only) |

### 8.4 Empty copy per screen (Blip pose · title · body · action)

| Screen / section | Pose | Title | Body | Action |
| --- | --- | --- | --- | --- |
| Home (no friends) | wave | `Your feed is waiting for friends` | `Add a friend and you'll see what they're playing here.` | `Invite friends` |
| Home Live now (none live) | sleepy | `No one's playing right now.` | — | `Send a song instead` |
| Home Live filter | sleepy | `No one's live right now.` | — | `Show everyone` |
| Quick send | sleepy | `Nothing played in the last day.` | — | `Search for a song to send` |
| Onboarding friends | wave | `No suggestions yet.` | `Invite a friend and you'll see them here.` | `Copy invite link` |
| Friends requests | sleepy | `No requests right now.` | — | `Share your invite link` |
| Friends suggestions | wave | `No suggestions yet.` | `As you and your friends listen, we'll find people you'd get along with.` | `Share your invite link` |
| Friends list | wave | `No friends yet` | — | `Invite friends` |
| Circles | wave | `Circles are small groups for your people.` | `Make one for your flatmates, your band or your college crew.` | `Create a circle` |
| Circle page (alone) | wave | `It's quiet in here.` | `Invite people to start the feed and this week's battle.` | `Invite to circle` |
| Blends | wave | `Blends mix your taste with friends'.` | `Pick up to 5 friends and we'll find songs you'll all like.` | `Make a Blend` |
| Blend (no data) | sleepy | `Not enough listening to blend yet.` | `Give it a few days of listening and try again.` | `Remind me` |
| Session queue | wave | `The queue is empty.` | `Add the first song.` | `Add a song` |
| Rituals (no circles) | wave | `Battles happen inside circles.` | `Join or create a circle to play this week.` | `Create a circle` |
| Battle (no nominations) | sleepy | `No songs nominated yet.` | — | `Nominate a song` |
| Recap not ready | sleepy | `Your {Month} recap arrives by the 2nd.` | — | `See last month` |
| Recap no data | sleepy | `Not enough listening in {Month} for a recap.` | — | `Connect your music` |
| Profile stats | sleepy | `Your stats are warming up.` | `They build over 2–4 weeks of listening.` | `Connect another app` |
| Inbox received | wave | `Nothing here yet.` | `When friends send you songs, they land here.` | `Send a song first` |
| Inbox sent | sleepy | `You haven't sent anything yet.` | — | `Send a song` |
| Notifications | cheer | `You're all caught up.` | — | `Notification settings` |
| Settings connections | wave | `No music apps connected.` | — | `Connect your music` |
| NowPlayingBar idle | sleepy | `Nothing playing.` | `Play something in your app and it shows up here.` | — |

---

## 9. Accessibility

Target: WCAG 2.2 AA, zero axe violations (NFR-A11Y-01), manual screen-reader pass per release with NVDA + Firefox, VoiceOver + Safari (macOS and iOS), TalkBack + Chrome.

### 9.1 Global keyboard map

Single-key shortcuts are off while focus is in a text field and can be turned off in Settings → Accessibility (2.1.4). `?` opens the shortcut dialog.

| Key | Action |
| --- | --- |
| `Tab` / `Shift+Tab` | Move between regions and controls (see focus order) |
| `/` | Focus search |
| `g` then `h` / `f` / `c` / `b` / `r` / `p` / `i` | Go to Home / Friends / Circles / Blends / Rituals / Profile / Inbox |
| `s` | Open Send sheet for my now-playing (or focused card's track) |
| `n` | Open notifications |
| `t` | Toggle theme |
| `Esc` | Close popover / sheet / dialog; clear search |
| `←` `→` | Move within shelf, chip row, carousel, tabs, recap faces |
| `Home` / `End` | First / last item in a shelf or list |
| `Enter` / `Space` | Activate; on a card, open Track detail |
| `u` / `d` | Upvote / downvote focused queue row (session) |
| `[` | Collapse/expand sidebar (≥ 1024) |

### 9.2 Focus order (AppShell)

Skip link → Sidebar (logo link, nav items, library) → TopBar (back/forward, search, inbox, notifications, theme, avatar) → main content in visual order (hero rotation control first, then slides, chips, each shelf as one stop via roving tabindex) → NowPlayingBar → (mobile) tab bar. Focus is never lost: when an item is removed, focus goes to the next item, else the previous, else the section heading. Focus-visible ring always visible and never obscured by the sticky TopBar or NowPlayingBar (2.4.11): `scroll-padding-top` = TopBar height + 8 and `scroll-padding-bottom` = bottom chrome + 8 on `main`.

### 9.3 ARIA patterns

- **Shelves:** `section[aria-labelledby]` > `ul[role=list][aria-label]` with roving tabindex; arrows as pointer-only controls (§4.5). Count announced in the heading: `Live now, 4 friends`.
- **HeroCarousel:** APG carousel (§4.20) with rotation control; autoplay stops on focus.
- **FilterChips:** radiogroup.
- **Tabs:** APG tabs.
- **Dialogs/sheets:** modal dialog pattern (§4.15).
- **Combobox search:** APG combobox with listbox groups.
- **Queue:** `ol` with per-row vote buttons (`aria-pressed`).
- **Charts** (timeline, compatibility): `role="img"` summary + a visually hidden data table.
- **Status chips:** text, not colour only (every state has a word and icon).

### 9.4 Live regions (polite and throttled)

- One app-level `div[aria-live="polite"][aria-atomic="true"]` (visually hidden) owned by an `Announcer` service; components never create their own live regions except Toast and form errors.
- **Live changes:** when friends start playing, the announcer batches events over a 30 s window and speaks at most once per 30 s: `Aanya is live on Spotify.` or `3 friends went live: Aanya, Dev and Riya.` Friends stopping are never announced. Track changes of already-Live friends are not announced. Nothing is announced while the user is typing, while a dialog is open, or when Settings → Accessibility → `Announce when friends go live` is off.
- **Queue reorders:** at most once per 5 s, only in an active session.
- **Send status:** `Aanya played your song.` at most once per minute (batched).
- **Errors:** `role="alert"` for blocking errors only.

### 9.5 Other checks

- Target size ≥ 44 × 44 (exceeds 2.5.8's 24 px). Dragging (sheet handle) always has a button alternative (2.5.7).
- No information by colour alone: Live = coral + `Live` word + bars; delayed = amber + word.
- Consistent help (3.2.6): `Help` link in avatar menu in the same place on every page.
- Redundant entry (3.3.7): onboarding never asks twice for name/birth year.
- Accessible authentication (3.3.8): password fields allow paste and password managers; no cognitive puzzles.
- Language `lang="en"`; page titles `{Page} · Jingle`.
- Images: artwork decorative inside labelled cards; Blip decorative.
- Reduced motion honoured per §6; `prefers-contrast: more` swaps `--text-muted` to `--text` and borders to `--border-strong`.

---

## 10. Honest-gap UI

In the web phase, Live exists only where a live-capable path exists (browser web players via the Companion, Spotify via its own link to Last.fm on any device, anyone who already uses ListenBrainz/Last.fm). Phone listening on YouTube Music, Apple Music and Amazon Music arrives as recent plays at best. We show this truthfully and quietly.

1. **Cards never error.** A friend whose phone plays can't be Live simply shows RECENT (`20 min ago on Apple Music`) or TOP. No warning icon, no "not supported", no setup prompt on a card or profile (BR-15).
2. **Say it where the user decides:** on the ConnectPlatformCard capability line and inside the Connect sheet promise:

| Platform | Card capability line | Connect sheet promise |
| --- | --- | --- |
| Spotify | `Live on any device` | `Friends see you live when you play, on your phone or computer.` |
| Apple Music | `Live in your browser · recent plays from your phone` | `You'll show as live when you play in your browser. Phone listening on Apple Music shows as recent plays, not live.` |
| YouTube Music | `Live in your browser · history by import` | `You'll show as live when you play in your browser. Phone listening on YouTube Music shows up after you import your history.` |
| Amazon Music | `Live in your browser` | `You'll show as live when you play in your browser. Phone listening on Amazon Music doesn't show yet.` |

(Spotify's any-device Live depends on the Last.fm link inside the Connect flow; if the user skips it, the line becomes `Live in your browser`.)

3. **Settings → Connections** repeats the honest note under each row, e.g. `Phone listening on Apple Music shows as recent plays, not live.`, `Phone listening on YouTube Music isn't shared yet. Import your history to include it.`, `Phone listening on Amazon Music isn't shared yet.` Plus `How this works` for route details and credits.
4. **Own NowPlayingBar:** if I'm playing on my phone on Apple Music, the bar shows my latest recent play with its true label; an info IconButton (`Why isn't this live?`) opens a popover with the same honest note and a link `Connection settings`. This is the only place outside Settings that explains the gap, and only to the user themself.
5. **Profile "platforms used"** shows text badges and share %, never capability warnings.
6. **Recap and stats** include recent plays from every source; they never claim live-derived metrics for gap platforms.
7. **Demo mode** reproduces gaps faithfully (ADR-0010): demo Amazon-phone friends never go Live.

---

## 11. Brand safety checklist

Run on every screen PR (design-system-engineer and code-reviewer).

- [ ] No logos, wordmarks, app icons, glyphs or favicons of Spotify, Apple Music, YouTube Music or Amazon Music anywhere (the Google sign-in button is rendered by Google Identity Services per Google's guidelines, not copied).
- [ ] Platform names only as PlatformBadge text in neutral Jingle colours; no platform brand colours (no Spotify green, Apple pink/red, YouTube red, Amazon blue/teal) on badges, buttons or cards.
- [ ] No platform fonts (e.g. Circular, SF Pro as brand, YouTube Sans, Amazon Ember); only Bricolage Grotesque, Inter, JetBrains Mono.
- [ ] No copied layouts: patterns are described in §12 and re-expressed with Jingle's grid, tokens, radii and components; no pixel-matching of any app's screens, iconography or spacing.
- [ ] Artwork shown is the release's cover art from permitted sources (Cover Art Archive, Apple Music, Spotify with attribution) or GenerativeCover; never platform marketing art, never grey squares.
- [ ] Spotify-sourced data (`attribution === "SPOTIFY"`) shows the text attribution `Data from Spotify` and a link back (`Open in Spotify`) on that card (ADR-0007). If Spotify's current branding guidelines require their logo for attribution, use only the official asset as supplied under those guidelines; decision recorded by design-system-engineer before S2 ships (open item).
- [ ] No route words on cards, profiles, notifications, toasts, emails, push, share images or page titles; allowed only on Settings → Connections and inside the Connect sheet (ADR-0002).
- [ ] Coral used only for Live; gradient only for the one primary action per view.
- [ ] Blip is original; no resemblance to other mascots.
- [ ] Share images (recap, podium) carry only Jingle branding and cover art; no platform marks.

---

## 12. Pattern sources

What we learned from each app's public UI, in our own words, and how Jingle re-expresses it. We borrow structure and ideas, never assets.

| Source app | Pattern observed (our description) | Why it works | Jingle version |
| --- | --- | --- | --- |
| Spotify | Persistent left navigation with a user-owned library list under it | Wayfinding is always one glance away; your own collections are first-class | Sidebar with Home, Friends, Circles, Blends, Rituals, Profile, then a Library of your circles and Blends with live counts |
| Spotify | Home built from dense horizontal rows of square covers, each row a theme | Lots of content in little vertical space; easy skim | Shelves `Live now`, `From your circles`, `Sent to you`, `People you may know` with snap scrolling and arrow buttons |
| Spotify | Always-present bottom bar for the current track | Continuity across pages | NowPlayingBar showing *my* current play plus quick Send and Private mode |
| Spotify | Dark-first canvas that lets cover art carry the colour | Art pops; calm at night | Dark default #08080B, light toggle, colour mostly from artwork and the one gradient CTA |
| Apple Music | Large, confident titles and a lot of breathing room on detail pages | Feels editorial and premium; hierarchy is obvious | Bricolage display type at 56 px on Profile, Circle and Blend headers with 48 px section spacing |
| Apple Music | Page colour sampled from the cover, translucent layers over blurred art | Every page feels unique and tied to its music | AmbientHeader: blurred art + clamped artwork colour wash + scrim; glass TopBar over it |
| YouTube Music | Row of filter chips across the top of Home | One tap narrows a busy feed | FilterChips `All`, `Live`, and one per circle |
| YouTube Music | A compact grid of quick-play songs chosen for you | Fast action without navigation | QuickSendGrid: your last day's tracks, one tap to Send to friends |
| YouTube Music | Mood and genre chips as entry points | Low-effort discovery | Genre chips in onboarding (cold-start taste twins) and on the Profile stats |
| Amazon Music | A clean, wide hero carousel at the top of Home | Promotes the one thing that matters this week | HeroCarousel of Blends, battle results, recaps and circle suggestions, with pause control |
| Amazon Music | Clear separation between "for you" and "what's popular" areas | Users understand why they're seeing something | Home separates friend activity (Live now, From your circles, Sent to you) from Jingle's suggestions (People you may know, circle suggestions), each suggestion carrying its reasons |

Research note: patterns were taken from general, long-standing public knowledge of these apps' web and mobile interfaces as of September 2026; no screenshots or assets are stored in this repository.

---

## Appendix A. Open items

1. Spotify attribution: text vs official logo (see §11); owner design-system-engineer + platform-researcher.
2. SRS JNG-01-02 Gherkin names ListenBrainz on the Sources screen; this spec places that token path inside the Connect sheet's `Other ways to connect` (allowed by ADR-0002) — qa-engineer should target the sheet.
3. CONTRACTS.md §7 does not list `Recently on {Platform}` in the grammar line but mentions it in the `observed_at` note; architect to add it to the grammar list for clarity.
4. Chat in sessions and concerts are not specified here beyond placement; they get their own addendum if scheduled.

## Appendix B — Decisions on Appendix A (Orchestrator, 2026-09-29)

1. **Spotify attribution:** ADR-0013 §5 — "Open Spotify" plus attribution on `attribution="SPOTIFY"` cards; official logo only when the human places the official asset (HUMAN_ACTIONS HA-7), else the text "Spotify".
2. **ListenBrainz token paste:** accepted — it lives in the Connect sheet under "Other ways to connect". The JNG-01-02 acceptance test targets the sheet (`# amended by UX_SPEC Appendix B`).
3. **"Recently on {Platform}":** added to the CONTRACTS.md §7 grammar.
