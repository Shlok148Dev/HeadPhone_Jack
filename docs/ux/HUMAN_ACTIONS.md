# Human actions for the redesign

Nothing waits on these; every screen already works with the fallbacks.

## HA-UX-1 Official platform badges (optional polish)
1. Download each platform's official assets from its own brand page only:
   - Spotify: <https://developer.spotify.com/documentation/design>
   - Apple Music: Apple's Marketing Guidelines, "Listen on Apple Music" badges
   - YouTube Music: <https://www.youtube.com/howyoutubeworks/resources/brand-resources/>
   - Amazon Music: the Amazon Music brand guidelines (from your Amazon partner contact)
2. Put them in `apps/web/public/brands/<platform>/`, each with a `SOURCE.md` (URL, date, rules: minimum size, clear space, colour use).
3. Tell Claude "badges added". It will swap the text badges for the official marks wherever the guidelines allow (never in a sentence, never altered).

## HA-UX-2 Apple MusicKit developer token (better covers and artist photos)
Needs Apple Developer enrolment (paid). Create a MusicKit key, then set `APPLE_MUSIC_TEAM_ID`, `APPLE_MUSIC_KEY_ID` and `APPLE_MUSIC_PRIVATE_KEY_PATH` in `.env`. Until then the free iTunes Search API supplies the covers.

## HA-UX-3 (optional) 21st.dev MCP key
Only useful for component inspiration; not needed.
