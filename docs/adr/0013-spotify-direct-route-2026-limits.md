# ADR-0013: Direct Spotify route under 2026 Development Mode limits

- Status: Accepted
- Date: 2026-09-29
- Source: `docs/research/spotify.md`

## Context
Research (checked 2026-09-29) found: Development Mode apps no longer receive `external_ids` (ISRC) or the user's email/country/product from `GET /me`; Policy III.13 forbids "derived listenership metrics … usage statistics, user metrics, or building profiles of users", which is broader than the III.14 ML-training ban; III.5 forbids products "integrated with streams or content from another service"; the design guidelines require Spotify's own logo when showing Spotify content.

## Decision
1. **Identity:** direct-Spotify tracks resolve via MusicBrainz (Spotify URL relationship where available) and then the fuzzy matcher. SRS 4.4 step 1 no longer applies to Spotify.
2. **Allowlist:** `SPOTIFY_ALLOWLIST` lists **Jingle account emails**; the dashboard still needs each tester's Spotify email (HUMAN_ACTIONS HA-1). A 403 from Spotify for a non-registered user sets the connection to `NEEDS_REAUTH` and the orchestrator falls back to the next route.
3. **Display-only, no analytics:** a second lineage flag `analytics_allowed` joins `trainable`. Both are false for `via = DIRECT, platform = SPOTIFY`. `permitted_for_analytics()` (py-common) must gate stats, compatibility, timeline, recap, battles, Blends and suggestions. Direct-Spotify events feed only the Live/Recent card and the user's own history view, and are deleted on unlink.
4. **III.5 risk accepted for the pilot:** direct Spotify stays optional, allowlisted, attributed, and never mixed into computed features (point 3). Spotify listeners get the full product through the Companion and Last.fm routes.
5. **Attribution:** cards with `attribution = "SPOTIFY"` show "Open Spotify" and a Spotify attribution. The official logo is shown only if the official asset has been placed at `apps/web/public/brand/spotify/` by a human following Spotify's guidelines (HA-7); otherwise the text "Spotify". The kickoff rule allows marks where a brand guideline permits them.
6. The 24-hour deletion bound is Jingle's own stricter rule (the policy requires deletion on disconnect). SRS "III.9 attribution" is a mis-citation; attribution rules are in the design guidelines.

## Conflicts resolved
SRS 4.4 (ISRC from Spotify) and CONTRACTS §5 (`trainable` only) vs 2026 platform reality: reality wins; CONTRACTS updated.
