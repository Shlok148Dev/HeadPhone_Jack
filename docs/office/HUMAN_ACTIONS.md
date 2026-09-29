# Human actions (only Shlok can do these)

Nothing in the build waits on these. Every feature below already works in demo mode (`JINGLE_DEMO=1`) and against recorded fixtures. Doing an item simply switches the real integration on.

After filling any value: `docker compose up -d --force-recreate core-api ingest-ml workers web`.

---

## HA-1 Create the Spotify developer app and add the 5 pilot testers

Unlocks: direct Spotify route (Live, Recent, Top for up to 5 people). Everyone else on Spotify uses Spotify's Last.fm link or the Companion extension.

Requirement: the account that **owns** the app must have Spotify Premium (Spotify rule since 11 Feb 2026).

1. Go to <https://developer.spotify.com/dashboard> and log in with the Premium account.
2. Accept the Developer Terms if asked.
3. Click **Create app**.
   - App name: `Jingle Pilot`
   - App description: `Social listening pilot for 10 friends`
   - Redirect URI: `http://127.0.0.1:8080/api/v1/sources/spotify/callback` then click **Add**. (Spotify no longer accepts `localhost`; use the IP exactly.)
   - "Which API/SDKs are you planning to use?": tick **Web API** only.
   - Tick the terms box, click **Save**.
4. On the app page open **Settings**. Copy **Client ID**; click **View client secret** and copy it.
5. Open the **User Management** tab. For each of up to 5 testers enter their name and the **email of their Spotify account**, click **Add user**.
6. In `.env` set:
   - `SPOTIFY_CLIENT_ID=` (Client ID)
   - `SPOTIFY_CLIENT_SECRET=` (Client secret)
   - `SPOTIFY_ALLOWLIST=` comma-separated emails **as used for their Jingle accounts** (they may differ from the Spotify emails; Jingle matches on the Jingle email).
7. For the pilot, open Jingle at `http://127.0.0.1:8080` (not `localhost`) so the redirect lands on the same origin.

Verify: sign in as an allowlisted user → Settings → Connections → **Connect Spotify** shows Spotify's own approval screen.

## HA-2 Get a free Last.fm API key

Unlocks: Spotify's built-in Last.fm scrobbling as a Live route for every Spotify user on every device, and Last.fm for anyone already scrobbling.

1. Log in (or sign up) at <https://www.last.fm>.
2. Go to <https://www.last.fm/api/account/create>.
3. Fill in: Contact email (yours), Application name `Jingle Pilot`, Application description `Non-commercial pilot`, Callback URL `http://127.0.0.1:8080/api/v1/sources/lastfm/callback`, Homepage blank.
4. Submit. Copy **API key** and **Shared secret**.
5. In `.env` set `LASTFM_API_KEY=` and `LASTFM_SHARED_SECRET=`.

Terms reminder (already built in): non-commercial use only, "powered by AudioScrobbler" credit on Settings → Connections, Last.fm data never used for model training.

Pilot users then do this once in Spotify (Jingle shows these steps inside its Connect Spotify sheet): Spotify app → Settings → Apps (or Privacy & social → "Connect to Last.fm" depending on app version) → connect Last.fm.

## HA-3 Create a Google OAuth client for "Sign in with Google"

Unlocks: Google sign-in (email sign-in works without it). Uses only `openid email profile`, which needs **no Google verification** while the app is in Testing with ≤ 100 test users.

1. Go to <https://console.cloud.google.com/>, create a project named `jingle-pilot`.
2. Left menu → **Google Auth Platform** (or APIs & Services → OAuth consent screen) → **Get started**.
   - App name `Jingle Pilot`, support email yours, Audience **External**, contact email yours → Create.
3. **Audience** → Test users → **Add users**: add each pilot user's Google email.
4. **Clients** → **Create client** → Application type **Web application**, name `jingle-web`.
   - Authorised JavaScript origins: `http://localhost:8080` and `http://127.0.0.1:8080` (add your server's https origin later).
   - Authorised redirect URIs: none needed (Jingle uses the Google Identity Services button).
   - Create. Copy the **Client ID** and **Client secret**.
5. In `.env` set `GOOGLE_OAUTH_CLIENT_ID=` and `GOOGLE_OAUTH_CLIENT_SECRET=`.

## HA-4 Fill in `.env` and generate real secrets

1. `cp .env.example .env`
2. Replace `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY`, `SERVICE_TOKEN` with fresh values: `python -c "import secrets;print(secrets.token_urlsafe(48))"` (run three times).
3. Replace `TOKEN_KEK_B64`: `python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"`, and set `TOKEN_KEK_ID=pilot-1`. **Back this key up offline**: losing it makes stored platform tokens unreadable (users would reconnect).
4. For real users set `JINGLE_DEMO=0`.
5. Optional web push: `npx web-push generate-vapid-keys` → `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`.

## HA-5 (later, not needed for the pilot) Approval-gated integrations

These are built and flagged off. Do them only when you move beyond the pilot.

| Item | Where | Unlocks | Flag |
| --- | --- | --- | --- |
| Apple Developer Program (USD 99/yr), MusicKit key | developer.apple.com → Certificates, IDs & Profiles → Keys → MusicKit | Apple Music recent plays and heavy rotation | `apple_music_enabled` |
| Amazon Music Web API access | Amazon developer business development contact | Amazon library sync | `amazon_music_enabled` |
| Google verification for `dataportability.myactivity.youtube` | Google Cloud console → OAuth verification | Automatic YouTube history | `google_dataportability_enabled` |
| Last.fm commercial agreement | partners@last.fm | Last.fm at scale and for training | — |
| Spotify Extended Quota | Spotify dashboard (needs registered business, 250k MAU) | Direct Spotify for all | allowlist removed |
| Ticketmaster Discovery API key (free signup) | developer.ticketmaster.com | Concert alerts | `concerts_enabled` |

## HA-6 Load the Jingle Companion extension (each pilot user)

1. `pnpm --filter @jingle/companion-extension build` (or download the built zip the admin shares).
2. Chrome/Edge → `chrome://extensions` → toggle **Developer mode** → **Load unpacked** → select `apps/companion-extension/dist`.
3. Click the Jingle icon → **Sign in to Jingle** (it opens Jingle and pairs automatically).
