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
- **D-ART-07** Second source: MusicBrainz + Cover Art Archive (open data, official web service, ≤ 1 request/second with back-off on 503). Used only when iTunes has no match by the right artist, which happens for some Latin and Indian-hip-hop originals where Apple's search returns only tributes. The MusicBrainz recording must match title and artist credit exactly after normalisation. Its images redirect twice to archive.org (about 3 s, sometimes stalling), so the client loads them through Next's image optimizer: cached 30 days on a `webcache` volume, after which they are served from our origin in about 6 ms. No image files are committed or stored in the database.
- **D-ART-08** The artist must match before scoring: results by other artists are dropped first, then the best title wins. Featured credits count ("Uptown Funk (feat. Bruno Mars)" belongs to Bruno Mars too). This rejects same-titled namesakes that previously passed on title alone.
- **D-ART-09** Group faces (Blends, Circles) use one `CoverMosaic`: four or more real covers make a 2×2 grid, fewer show the first cover whole, none shows the generative cover. Avatars sit *below* the mosaic, never on it. Circle covers come from each member's card as the viewer is allowed to see it (`resolve_card`), so a tile never reveals more than the feed.
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
- **D-DS-06** Buttons are `relative` only when the caller doesn't position them; previously `relative` silently beat `absolute`, pushing in-field controls (the password eye) out of the field.
- **D-DS-07** Selected filter chips are a solid inverted chip, not the brand gradient, so Home keeps its three brand moments (nav marker, hero action, Send).
- **D-COPY-01** Gateway errors (502–504) say "Jingle can't be reached right now. Try again in a moment." Server-side errors without an envelope say "Something went wrong on our side." The user is never implied to be at fault.
- **D-COPY-02** Greetings use the first name; a placeholder name ("You (demo)") gets no name rather than "Good evening, You".
- **D-DS-08** `sm` is 640 px (was 390). At 390, every `sm:` row layout (the search pill text, recap and battle rows) switched on for ordinary phones and overflowed. Phones (360–639) get the base layout.
- **D-PERF-01** Animation ships light: components import `motion/react-m` (as `motion`), and `<LazyMotion features>` in providers loads the full feature set (layout, layoutId, drag) right after first paint; `optimizePackageImports: ["motion"]` tree-shakes the rest. First-load JS dropped by about 25 kB on every route (Home 181 → 156 kB, landing 169 → 145 kB). Shell presence panels are lazy too.
- **D-ART-10** Covers are responsive: the Artwork component derives a srcset from any payload URL (Apple CDN 160–1400 px from one path; Cover Art Archive 250/500/1200 through the image cache). The browser picks the size from the rendered width × DPR. Hero and auth art load eagerly at high priority.
- **D-ART-06 (revised)** While a cover loads, show a calm surface in its own dominant colour. The busy generative pattern flashing on every load read as low quality. Generative covers are now for truly missing art only.
- **D-ONB-02** Sign-in and sign-up are a viewport-locked split: the form on the left, vertically centred, never below the fold. The live cover wall fills the right from 768 px (2 columns, 3 from 1024 px), and phones get a strip of real covers above the form. The page is never artless.
- **D-SHELL-04** Friend activity is a panel the user opens from the top bar (remembered per device), closed by default. It overlays at lg and docks at xl. The sidebar "Live now" list shows when it is closed.
- **D-BRAND-02** (supersedes D-BRAND-01; the founder asked for real logos, 2026-10-02.)
  - **Sources:** official marks from Simple Icons for Spotify, Apple Music and YouTube Music (CC0 paths), and a public-domain Wikimedia Commons file for the Amazon Music wordmark.
  - **Placement:** unmodified, in brand colour, at text size, beside the platform name on badges, feed labels, the open-in-app action, friend activity and friend rows.
  - **Trademarks** remain with their owners; the guideline check is HA-UX-1.
- **D-HOME-01** Home opens on the **Now stage**: one song a friend is playing, in its own colour (ambient), with a big cover, the friend's Pulse and **Tune in** as the one primary action. Live friends come first (server state only); otherwise the freshest recent plays. It rotates every 9 s, pauses on hover or focus, and stays still under reduced motion. Then **Today's Drop**, then rituals and shelves.
- **D-TUNE-01** Tune in: open the song in *your* app, whatever app your friend used.
  - Order: your app's exact link, then a search in your app, then the friend's app, then any exact link.
  - Wording is honest: "Play in X" only for an exact link, "Find in X" for a search.
  - Apple Music exact links come from the strict iTunes match (the catalogue song id).
  - Exact Spotify, YouTube Music and Amazon Music links would need those platforms' catalogue APIs (or a cross-platform matcher such as Odesli), which is not adopted without a terms review.
- **D-DROP-01** Daily Drop (JNG-14-01). One song per person per local day, final once posted. Friends' drops stay **sealed** until you drop: you see who dropped, never what. That trade is the daily habit loop. A streak counts consecutive days. Demo personas drop between 06:00 and 13:00; the demo login never drops automatically.
- **D-DS-09** Buttons add `inline-flex` only when the caller doesn't hide them (`hidden lg:inline-flex`). The base class used to win, so the Friend activity toggle appeared on phones (same family as D-DS-06).
- **D-HOME-02** (founder, 2026-10-02) Home shows friends' listening **once**, in the Now stage. The "Live now" shelf, the "Everyone else" grid and the circle filter chips are removed: the same friends appeared up to four times (stage, shelf, grid, activity panel). Loading, error and "no friends yet" states moved to the stage's slot; with friends but no plays, the stage shows a quiet one-line state. A circle's listening lives on its circle page (JNG-05-03 now verified there). "From Spotify" stays as its own attributed module (D-BR-01).
