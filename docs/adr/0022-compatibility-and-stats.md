# ADR-0022: Compatibility, stats and taste timeline (Sprint 9)

- Status: Accepted
- Date: 2026-10-01

## Decisions

1. **Formula as Technical Bible 6.1**, computed over 90 days of *analysable* listens (direct-Spotify API data never counts, BR-03).
   - Artists: weighted Jaccard over the top 50 by play share.
   - Genres: cosine of genre-share vectors built from MusicBrainz artist tags.
   - Sound needs at least 20 analysed recordings per person. The pilot runs no audio analysis, so `audio_features_available` is always false, the no-sound weights apply (0.6 / 0.4), and the card says "Sound comparison unavailable" (Gherkin JNG-08-01/02).

2. **When genres are unknown** for either person, the genre component is left out rather than guessed. Artists carry the full weight and the card says "Genre comparison unavailable".

3. **F_pairs percentile.** A monthly job (1st of the month, 05:00) stores the sorted raw scores of every friend pair: numbers only, no identities.
   - With fewer than 20 pairs the score falls back to `round(100 x raw)` and is flagged `calibrated: false`.
   - The UI then says "Scores settle as more friends join Jingle".

4. **Access.** Compatibility is shown only for a friend whose activity the viewer may see (BR-06/07, visibility, Private mode). BR-09 is enforced twice:
   - The API returns no score without a breakdown.
   - `CompatibilityMeter` refuses to render a bare number.

5. **Thresholds.**
   - A score needs at least 20 plays each in 90 days. Below that the card says "Not enough listening yet".
   - My stats appear after 14 days of data. Before that, a "builds over 2-4 weeks" empty state (JNG-08-06) shows the days remaining.

6. **Minutes** sum the known track durations. Plays with no duration count as about 3.5 minutes, which is why the UI says "about".

7. **Timeline.** Twelve calendar months: plays, top artist and top genres per month. The visual chart has a screen-reader table equivalent.

8. **Demo genres.** Demo mode seeds artist tags for the 18 catalogue artists, standing in for MusicBrainz tags, which need network resolution. This is a demo-only exception, like the demo scrobble tokens in ADR-0010.

9. **Profiles** (`GET /users/{username}`): college and city are shown only to friends or to me. Blocked either way gives 404.
