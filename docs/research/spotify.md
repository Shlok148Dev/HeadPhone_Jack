# Spotify Web API: Development Mode, OAuth, endpoints, policy

Checked: 2026-09-29. Owner: platform-researcher.

> Verification note: the quota, redirect-URI, rate-limit, February 2026 migration, endpoint reference, Developer Policy and Design Guidelines pages were all read today.

## Question
What exactly can Jingle's direct Spotify route do in 2026 under Development Mode, and which policy clauses constrain it?

## Impact (contradictions with CONTRACTS / ADRs / .env.example / source docs)

1. **ISRC is gone in Development Mode.** The Feb 2026 migration removed `external_ids` (and `popularity`, `available_markets`, `linked_from`) from Track and Album objects for Dev Mode apps. Tech Bible §2.2 ("ISRC from `external_ids`") and SRS §4.4 step 1 ("match by ISRC … Spotify") do not hold. Identity resolution for direct-Spotify listens must fall back to MusicBrainz: first a URL-relationship lookup on the track's `open.spotify.com` URL (inferred, see `musicbrainz-coverart.md`), then fuzzy artist/title. Needs an ADR amending SRS 4.4.
2. **`GET /me` no longer returns `email`, `country` or `product` in Dev Mode.** `SPOTIFY_ALLOWLIST` ("comma-separated emails") cannot be checked against the Spotify profile. The allowlist must be keyed on the **Jingle** account email (or Spotify user `id` captured after first link), and the human must add the user's **Spotify** account email in the dashboard separately. Non-listed users get HTTP 403 from the API after consent. Update the `.env.example` comment and HUMAN_ACTIONS.
3. **Policy III.13 bans analysis, not only ML.** "Do not analyze the Spotify Content … creating new or derived listenership metrics … usage statistics, user metrics, or building profiles of users". `trainable = false` (CONTRACTS §5, ADR-0007) only covers training. Direct-Spotify events must also be excluded from stats, compatibility, taste timeline, recaps, battles, Blends and suggestions (S5, S7–S10). Recommend renaming/broadening the lineage helper (e.g. `permitted_for_analysis()`), or adding an `analyzable` flag to the event contract. ADR needed.
4. **Policy III.5 risk.** "Do not create any product or service which is integrated with streams or content from another service." A cross-platform feed mixing Spotify API data with Apple/YouTube/Amazon data is arguably within this clause. Keeping the direct route to 5 testers, display-only and attributed (ADR-0007) limits exposure, but the architect should record the risk in an ADR and keep direct Spotify optional (Companion and Last.fm routes are not Spotify API data).
5. **Redirect URI host vs PUBLIC_BASE_URL.** `SPOTIFY_REDIRECT_URI=http://127.0.0.1:8080/...` is correct (localhost is forbidden), but `PUBLIC_BASE_URL=http://localhost:8080`. Browsers treat `localhost` and `127.0.0.1` as different sites, so the `jingle_refresh` cookie and any PKCE verifier/state cookie set on `localhost` will not reach the callback on `127.0.0.1`. Either set `PUBLIC_BASE_URL=http://127.0.0.1:8080` for local, or keep the PKCE `state`/`code_verifier` server-side (Redis keyed by `state`) and redirect back to `PUBLIC_BASE_URL` after the callback. Production needs HTTPS.
6. **Attribution vs brand-safety rule (verified).** Spotify's Design Guidelines say partner integrations "should always use our full logo (icon + wordmark)" when displaying Spotify content (icon alone only when space is limited; min 70 px full logo, 21 px icon). PLAN §3 rule 6 allows only text badges. A text-only badge on cards with `attribution = "SPOTIFY"` does not meet Spotify's rule. Using Spotify's official, unmodified asset under its guidelines is licensed use, not copying; an ADR should permit it **only** on direct-API content (card and Settings → Connections). Artwork from the API must also get 4 px (small/medium screens) or 8 px (large) corner radius, never cropped or overlaid, which constrains the card design.
7. **Deletion window.** The Policy (effective 15 May 2025) says delete on disconnect (I.2) with no hour figure; ADR-0007's 24 h is a Jingle/SRS rule and is stricter. No change needed, but cite I.2, not a Spotify "24 h" clause.
8. **Clause numbering.** SRS cites "III.9 attribution"; in the current Policy III.9 is data transfer to other services and attribution is in section II. Fix references.

## Findings

### Development Mode (verified, official doc)
- Up to **5** authenticated users per Dev Mode app; the **app owner must have active Spotify Premium** or the app stops working.
- Feb 2026 changes: new Dev Mode apps from **2026-02-11**, existing apps migrated **2026-03-09**. Client IDs per developer: 1, raised to **25 as of July 2026**; quota counted per developer account.
- Removed for Dev Mode: batch `GET /tracks|/albums|/artists…`, `GET /artists/{id}/top-tracks`, browse endpoints, `GET /users/{id}`, `GET /users/{id}/playlists`, `POST /users/{user_id}/playlists`, `GET /markets`; library PUT/DELETE replaced by `/me/library`. `/playlists/{id}/tracks` renamed `/playlists/{id}/items`; playlist contents only for playlists the user owns or collaborates on. Search `limit` max 10.
- Removed fields: Track `external_ids`, `popularity`, `available_markets`, `linked_from`; User (`/me`) `country`, `email`, `explicit_content`, `followers`, `product`.
- Player endpoints (`currently-playing`, `recently-played`) and `/me/top/{type}` are not listed as removed.
- Extended Quota (since 2025-05-15): organisations only, registered business, launched service, **≥ 250k MAU**, key markets; review up to six weeks. Unreachable for the pilot.
- Dev Mode quota exceeded → `429` with reason `QUOTA_EXCEEDED`.

### Redirect URIs (verified)
- HTTPS required except loopback; loopback must be the literal `http://127.0.0.1:PORT` or `http://[::1]:PORT`; **`localhost` is not allowed**. Registered URI must match exactly (port may be omitted at registration for loopback only). Enforced for new apps from 2025-04-09, all clients from November 2025.

### OAuth (verified for scopes; PKCE flow inferred from standard docs)
- Authorization Code with PKCE: `GET https://accounts.spotify.com/authorize?response_type=code&client_id&redirect_uri&scope&state&code_challenge_method=S256&code_challenge`, then `POST https://accounts.spotify.com/api/token` (`grant_type=authorization_code`, `code`, `redirect_uri`, `client_id`, `code_verifier`). Refresh with `grant_type=refresh_token`; a new refresh token may be returned and must replace the stored one (inferred).
- Scopes: `user-read-currently-playing` (currently playing), `user-read-recently-played` (recent), `user-top-read` (top). Add `user-read-playback-state` only if device info is needed (inferred). Playlist write (Blends) would need `playlist-modify-private`/`playlist-modify-public` (inferred).

### Endpoints (verified)
- `GET /v1/me/player/currently-playing?additional_types=track,episode` → `timestamp` (ms), `progress_ms`, `is_playing`, `item`, `currently_playing_type` (`track|episode|ad|unknown`), `context`. Nothing playing → `204 No Content` (inferred; doc lists only 200).
- `GET /v1/me/player/recently-played?limit≤50&after|before` (ms, mutually exclusive) → `items[].track`, `items[].played_at`, `items[].context`, `cursors`. No podcast episodes.
- `GET /v1/me/top/{artists|tracks}?time_range=short_term(~4 wk)|medium_term(~6 mo, default)|long_term(~1 yr)&limit≤50&offset`.

### Rate limits (verified)
- Rolling **30-second** window; over it → `429` with `Retry-After` (seconds). Spotify publishes no number. Dev Mode limits are lower than Extended.

### Developer Policy (verified, effective 2025-05-15)
- I.2: provide an easy disconnect; on disconnect delete and stop processing the user's personal data.
- II: attribute Spotify Content as supplied by Spotify; metadata and cover art **must link back** to the album/content/playlist on Spotify; no standalone metadata/artwork service.
- III.5 (other-service integration), III.9 (no transfer to another service except the user's own data/playlist metadata), III.11 (no replicating core Spotify UX), III.13 (no analysis/metrics/profiles), III.14 (no ML training or ingestion into ML) — quoted above.
- IV: non-streaming SDAs may monetise only via ads/sponsorship or selling access.

### Branding (verified, official Design Guidelines)
- App name must not include "Spotify" or sound/look similar; "for Spotify" is acceptable wording. Jingle's logo must not resemble Spotify brand elements. Writing "Spotify" as text to name the platform (e.g. "Live on Spotify") is fine.
- Attribute Spotify content with the **full logo (icon + wordmark)**; icon only when space is limited. Minimum 70 px (logo) / 21 px (icon).
- Metadata (track, artist, album, playlist titles) must be shown as supplied by Spotify and legible.
- Artwork unmodified: no crop, overlay or distortion; corner radius 4 px (small/medium) or 8 px (large).
- Link-back labels: "OPEN SPOTIFY", "PLAY ON SPOTIFY" or "LISTEN ON SPOTIFY" (or "GET SPOTIFY FREE" if not installed).

## Constraints for Jingle
- Direct route: ≤ 5 testers, owner Premium, display-only, attributed with link-back, excluded from all analytics and ML, deleted on unlink.
- Poll `currently-playing` at 20 s for 5 users is well within limits; always honour `Retry-After`.

## Sources
- https://developer.spotify.com/documentation/web-api/concepts/quota-modes
- https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide
- https://developer.spotify.com/documentation/web-api/concepts/redirect_uri
- https://developer.spotify.com/documentation/web-api/concepts/rate-limits
- https://developer.spotify.com/documentation/web-api/reference/get-the-users-currently-playing-track
- https://developer.spotify.com/documentation/web-api/reference/get-recently-played
- https://developer.spotify.com/documentation/web-api/reference/get-users-top-artists-and-tracks
- https://developer.spotify.com/policy
- https://developer.spotify.com/documentation/design
- https://techcrunch.com/2026/02/06/spotify-changes-developer-mode-api-to-require-premium-accounts-limits-test-users/ (secondary)
