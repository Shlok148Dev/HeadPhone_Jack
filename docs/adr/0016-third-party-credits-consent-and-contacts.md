# ADR-0016: Credits, Last.fm consent, MusicBrainz contact, Amazon key

- Status: Accepted
- Date: 2026-09-29
- Source: `docs/research/lastfm.md`, `musicbrainz-coverart.md`, `amazon-music.md`, `apple-musickit.md`

1. **Last.fm consent:** linking Last.fm (even by public username) shows an explicit consent step and records consent purpose `lastfm_link` (Last.fm ToS 2.8 for users outside the EEA).
2. **Credits placement:** the "powered by AudioScrobbler" credit (as text with a link to Last.fm) and the ListenBrainz credit appear on Settings → Connections and inside the Connect sheet where the user links Last.fm. Cards carry no route credits (BR-14). This is a judgement call: the credit is shown wherever the user acts on Last.fm data sourcing, not on every derived surface.
3. **MusicBrainz:** requests need a real contact in the User-Agent. New env `MUSICBRAINZ_CONTACT` (email or URL, set by the human). When empty, MusicBrainz lookups are disabled and resolution falls back to local fuzzy matching. The 1 req/s limit is a Redis bucket shared by all processes. Cover Art Archive images are displayed by URL only, never bundled or used for training.
4. **Amazon Music:** new env `AMAZON_MUSIC_API_KEY` (flagged adapter only); the adapter declares live/recent/top unsupported until approved docs say otherwise.
5. **Apple Music (flagged):** recently played items have no timestamps; such events carry `played_at_estimated = true` and render as "Recently on Apple Music".
6. **Local origin:** `PUBLIC_BASE_URL` defaults to `http://127.0.0.1:8080` so the Spotify loopback redirect and Jingle's cookies share one origin. OAuth `state` and PKCE verifiers are stored server-side (Redis, 10 min) keyed by `state`, never in cookies.
