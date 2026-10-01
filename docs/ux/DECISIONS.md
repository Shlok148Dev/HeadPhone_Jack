# Design decisions (redesign R1, "Night Studio")

One line of reasoning each. Priority when sources conflict: SRS business rules → platform brand and artwork rules → WCAG 2.2 AA → the design language → skill advice.

## Process
- **D-PROC-01** No subagent team. The founder's standing rule is no agents unless really necessary; the Orchestrator does the studio work.
- **D-PROC-02** Third-party skills and MCP servers (Impeccable, Taste, UI UX Pro Max, Emil's skills, Vercel and Addy Osmani skills, Playwright/DevTools/Context7/shadcn/21st MCPs) are **not installed**. Installing them means running unvetted code via `npx` without explicit permission. Their principles (anti-slop rules, motion craft, web-design guidelines, CWV and a11y audits) are applied from knowledge, and checks run with the repo's own Playwright, axe and build budgets.
- **D-PROC-03** No GSAP and no Lenis. Motion is already in the bundle, and CSS scroll-driven animations do the landing reveals with zero JS.

## Design system
- **D-DS-01** Night Studio surfaces: warm blacks (#0A090C → #252129) and warm paper for light (#F6F2EC → #E5DED4). Never pure grey. The contrast tests gate every pair.
- **D-DS-02** Film grain: one fixed SVG-noise layer at about 3 %. It is cheap (no repaint on scroll) and gives large surfaces depth.
- **D-DS-03** Radii: artwork 4 px small and 8 px large; cards 12; sheets 20; pills full.
- **D-DS-04** Generative fallback covers are muted (saturation 40–56 %, dark bases), so a missing cover reads as a quiet design rather than a neon placeholder. The grey guard moved from saturation ≥ 50 to ≥ 35.
- **D-DS-05** Colours stay hex, not OKLCH. The contrast tests compute WCAG ratios from sRGB, and the CSS mirror test compares exact strings. OKLCH would add churn with no visual gain.
- **D-DS-06** UI font: Geist over Inter (ADR-0024). It is tighter and more distinctive at 13–15 px in dense lists, with good tabular numerals, and is free (SIL OFL) via `next/font/google`.

## Artwork
- **D-ART-01** Real covers come from Apple's public iTunes Search API now (no key). The MusicKit catalogue replaces it once HA-UX-2 provides a developer token. Spotify images are used only on Spotify-attributed cards.
- **D-ART-02** Lookups never call the network. Misses are queued in Redis, and a worker resolves about 15 a minute (iTunes asks for roughly 20 a minute). `manage.py resolve_artwork --demo` fills the demo catalogue.
- **D-ART-03** Artist images: the artist's own album cover from iTunes (real artwork, one source, no new terms), falling back to a cover of one of their resolved songs. Deezer artist photos were not adopted: they would add another terms surface for marginal gain.
- **D-ART-04** Colours are extracted server-side with Pillow (median-cut). `ambient_dark` and `ambient_light` are lightness-shifted until theme text reads at ≥ 4.5:1, checked on the rounded hex that is actually emitted.
- **D-ART-05** Matching prefers the original recording: title and artist overlap, minus variant words (lo-fi, remix, sped-up, karaoke…) unless they were asked for. Weak matches are stored as **missing** and fall back to the generative design, never a wrong cover.
- **D-ART-06** No ThumbHash. Placeholders are the generative cover painted first, then the real image fading in. That is never grey and needs no extra dependency.

## Signatures and screens
- **D-SIG-01** The Pulse: a breathing coral ring for Live, a still neutral ring for Recent. Live and its coral move off the artwork onto the person (the brief's artwork rule).
- **D-SIG-02** The Room: the cover hero on its ambient field, participants orbiting slowly (counter-rotated to stay upright), and the queue re-ordering with spring layout animation.
- **D-SIG-03** Taste Constellation: two overlapping fields of real artist images, with shared artists larger in the overlap. It is decorative; the caption and breakdown carry the meaning.
- **D-SIG-04** Podium: rises 3, 2, 1. On the landing page it is scroll-driven; in the app it uses spring entries.
- **D-SIG-05** Recap story: full screen, with progress bars, tap or arrow keys, Space or hold to pause, Esc to close. Reduced motion disables auto-advance.
- **D-SHELL-01** Sidebar "Live now" shows at 1024–1439 px and the right "Friend activity" panel at ≥ 1440 px, so the two never duplicate each other.
- **D-SHELL-02** The active nav marker is a gradient bar: one of the three allowed brand moments.
- **D-SHELL-03** The ⌘K/Ctrl+K command palette (people, songs, circles, actions) is lazy-loaded so Home stays at 180 kB.
- **D-LAND-01** The landing hero is server-rendered with real covers (revalidated hourly). The headline sits *beside* the cover wall, never over it.
- **D-LAND-02** Scroll reveals use CSS `animation-timeline: view()` with fill-mode none, so content is visible by default. Motion's `whileInView` server-rendered at opacity 0 and hid content from no-JS readers and full-page captures.
- **D-BR-01** Spotify Web API cards render only in a separate, attributed "From Spotify" module on Home. They are never interleaved with other platforms.
- **D-BRAND-01** Platform marks stay as designed text badges until official assets are fetched (HA-UX-1). Downloading brand files needs the founder's go-ahead, and text badges are permitted by every guideline.
