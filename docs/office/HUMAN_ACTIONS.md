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
5. Set `MUSICBRAINZ_CONTACT=` to your email or the repo URL (MusicBrainz requires a real contact; without it Jingle matches tracks locally only).
6. Optional web push: `npx web-push generate-vapid-keys` → `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`.

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

## HA-7 (optional) Spotify attribution logo

Spotify's design guidelines require its official logo next to Spotify-sourced content. Jingle shows the text "Spotify" until the official asset is added.

1. Go to <https://developer.spotify.com/documentation/design> and download the official logo pack.
2. Put the full-colour logo (icon + wordmark) SVGs in `apps/web/public/brand/spotify/` as `logo-white.svg` and `logo-black.svg`, unmodified.
3. Rebuild the web image. Only direct-Spotify cards (5 testers) use it.

## HA-8 Put the pilot on a server (when you're ready to invite the 10)

Unlocks: friends using Jingle from their own phones and laptops over HTTPS.

1. Rent a 4 vCPU / 8 GB Ubuntu 24.04 server (for example Hetzner CPX31). Install Docker Engine and the Compose plugin.
2. Point a domain or subdomain (A record) at it.
3. Follow [`docs/runbooks/deploy-pilot.md`](../runbooks/deploy-pilot.md) step by step: `.env` values, one `docker compose` command, make yourself staff, add backups to cron.
4. Update the Spotify, Last.fm and Google redirect URIs (HA-1…3) from `http://127.0.0.1:8080` to `https://<your-domain>`.

Verify: open `https://<your-domain>`, sign up, connect a source, and see your card on Home.

## HA-9 (optional) Ticketmaster key for concerts (EP-10)

Concerts are not built in the pilot. EP-10 is all Should/Could except "attendance private by default", which has nothing to protect until concerts exist. To build them later, get a free key at <https://developer.ticketmaster.com> (Discovery API) and set `TICKETMASTER_API_KEY` in `.env`.


## HA-CONNECT-1 Last.fm keys (so Spotify works for everyone beyond the 25 testers)
1. Go to https://www.last.fm/api/account/create and sign in.
2. Create an API account:
   - Application name: **Jingle**
   - Callback URL: `<your Jingle address>/api/v1/sources/lastfm/callback`
3. Put the key and the shared secret in `.env` as `LASTFM_API_KEY` and `LASTFM_SHARED_SECRET`. Never paste them in chat.
4. Run `docker compose up -d`.

## HA-CONNECT-2 Spotify allowlist (up to 25 people get Spotify's own login)
1. In the Spotify Developer Dashboard, open the app → **User Management**.
2. Add each tester's **Spotify account email**.
3. Put the same emails in `.env` as `SPOTIFY_ALLOWLIST`, comma-separated.

Everyone else connects Spotify through Last.fm automatically.

## HA-CONNECT-3 Publish the Chrome extension (desktop YouTube Music / Amazon Music)
1. Register at https://chrome.google.com/webstore/devconsole (one-time US$5).
2. Zip the contents of `apps/companion-extension/dist` (run `npm run build` there first).
3. Upload the zip and fill in the privacy fields: it reads only the four music sites and sends plays to Jingle.
4. Once it's approved, set `EXTENSION_STORE_URL` in `.env` to the store link.

The Connect screen then shows **Add Jingle to Chrome**, and the extension connects itself after install.

## HA-CONNECT-4 Build and publish the Android app (phone listening)
1. Install Android Studio (it brings the Android SDK and JDK 17) and open `apps/android`.
2. Build with `./gradlew assembleRelease -PjingleUrl=https://<your Jingle address>`.
3. Register at https://play.google.com/console (one-time US$25) and upload the build.
   - Declare notification-listener use as **"show friends what music you play"**.
4. Set `ANDROID_APP_URL` in `.env` to the Play link.

## HA-CONNECT-5 Apple Music sign-in
This uses the same keys as HA-UX-5: an Apple Developer membership (US$99 a year) and a MusicKit key. Put them in `APPLE_MUSIC_TEAM_ID`, `APPLE_MUSIC_KEY_ID` and `APPLE_MUSIC_PRIVATE_KEY_PATH`.

Once they're set, the Apple Music tile opens Apple's own sign-in.
