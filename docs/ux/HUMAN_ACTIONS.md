# Human actions for the redesign

Nothing waits on these; every screen already works with the fallbacks.

## HA-UX-1 Platform marks: guideline check before public launch
The founder asked for real logos (2026-10-02). The marks now ship in `apps/web/src/components/ds/platformMarks.ts`:
- Spotify, Apple Music and YouTube Music icons: from Simple Icons (CC0 path data).
- Amazon Music wordmark: from Wikimedia Commons (a public-domain file).

They are shown unmodified, in brand colour, at text size, beside the platform name. The marks are still their owners' trademarks. Before a public launch:
1. Read each guideline: Spotify <https://developer.spotify.com/documentation/design>, Apple Music marketing guidelines, YouTube brand resources <https://www.youtube.com/howyoutubeworks/resources/brand-resources/>, and Amazon Music brand guidelines.
2. Check minimum size, clear space and colour rules. Spotify requires its full logo, not just the icon, in some contexts, and Apple prefers its official "Listen on Apple Music" badge for links.
3. Replace any mark that needs the official asset file: put it in `apps/web/public/brands/<platform>/` with a `SOURCE.md` and tell Claude.

## HA-UX-2 Apple MusicKit developer token (better covers and artist photos)
Needs Apple Developer enrolment (paid). Create a MusicKit key, then set `APPLE_MUSIC_TEAM_ID`, `APPLE_MUSIC_KEY_ID` and `APPLE_MUSIC_PRIVATE_KEY_PATH` in `.env`. Until then the free iTunes Search API supplies the covers.

## HA-UX-3 (optional) 21st.dev MCP key
Only useful for component inspiration; not needed.

## HA-UX-4 Logo originality check (before public launch)
The cassette-and-earphones mark started as an AI-generated concept. Before launch, run a reverse-image search and a trademark search (India: IP India public search; plus WIPO Global Brand Database) for similar marks in class 9/41/42. If anything close turns up, adjust the drawing (`apps/web/src/components/app/LogoMark.tsx`) before filing.
