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

## HA-UX-5 Switch on "Play in order in your app" (JNG-04-09)
Each app's button goes live as soon as its keys are in `.env`; then run `docker compose up -d`. Never paste keys into chat.

**Spotify (free; up to 25 named users in Development Mode)**
1. developer.spotify.com → Dashboard → Create app → APIs: Web API.
2. Redirect URIs: add `http://127.0.0.1:8080/connect/spotify/callback` (and your production domain's `/connect/spotify/callback`).
3. Users and access: add each tester's Spotify email (max 25 until Spotify grants extended quota).
4. `.env`: `SPOTIFY_CLIENT_ID=` (no secret needed: the browser uses PKCE).

**YouTube Music (free; Google review needed before the public can use it)**
1. console.cloud.google.com → new project → enable **YouTube Data API v3**.
2. Credentials → **API key**, restricted to YouTube Data API v3 → `.env` `YOUTUBE_API_KEY=` (server-side matching only).
3. OAuth consent screen → add scope `.../auth/youtube`, add yourself as a test user. Production needs Google's verification for this sensitive scope.
4. Credentials → **OAuth client ID (Web)**, Authorized JavaScript origins `http://127.0.0.1:8080` (and production) → `.env` `GOOGLE_OAUTH_CLIENT_ID=` (also powers "Continue with Google").
5. Quota: 10,000 units/day by default. Each new song match costs 100 (cached forever per song), and each song added to a playlist costs 50. Request more quota before launch.

**Apple Music (Apple Developer Program, US$99/year)**
1. developer.apple.com → Certificates, IDs & Profiles → Keys → create a key with **MusicKit** → download `AuthKey_XXXX.p8` (once only).
2. Put it outside the repo, mounted read-only into core-api, e.g. `secrets/AuthKey_XXXX.p8`.
3. `.env`: `APPLE_MUSIC_TEAM_ID=`, `APPLE_MUSIC_KEY_ID=`, `APPLE_MUSIC_PRIVATE_KEY_PATH=/run/secrets/AuthKey_XXXX.p8`.

**Amazon Music:** no public API can create playlists; Amazon users keep song-by-song play.
