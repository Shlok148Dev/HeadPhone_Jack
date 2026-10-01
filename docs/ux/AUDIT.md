# Audit of the pre-redesign UI (October 2026)

Screens were captured from the S1–S11 build (`artifacts/screenshots/s1`, all routes, both themes, 1440 and 390 px).

| Screen | Stock, static or generic | Why it fails |
| --- | --- | --- |
| Every card | **No real artwork.** Bright neon generative covers stood in for every song | Looked like a template. Covers carried no recognition, and the neon competed with everything, including Live |
| Feed cards | A **"LIVE" chip drawn on the artwork**; a coral ring tied to the art; truncated "Search in …" buttons | Broke the never-on-artwork rule. Live read as a sticker, not a person. Buttons were unreadable |
| Landing | Template hero: a headline beside a column of example cards, a big empty left half on desktop, three generic feature tiles with the mascot | No story, no real music, nothing that said "your friends" |
| Shell | Plain rail and top bar; no search; no sense of people; the now-playing bar only | Missed the two things that make Jingle Jingle: who's live, and getting to people fast |
| Home | Flat shelves; no hero; no "Sent to you"; E2E test circles leaking into the chips | Static, with no highlights from Blends, battles or recaps |
| Sessions | A form-like page: header, small cover, list | No sense of a shared room |
| Profile / compatibility | A score ring and bars | No people or artists, and no imagery |
| Recap | A small flip card | Not a moment worth sharing |
| Surfaces and type | Neutral blue-grey surfaces; Inter everywhere; flat cards | Generic. Nothing warm or studio-like; no depth |

## What changed in R1 (see STATUS.md)
- Real covers everywhere, through the Artwork service.
- Night Studio tokens, Geist, film grain, artwork glow.
- The Pulse, with nothing on the art.
- A new shell: Live now, Friend activity, ⌘K.
- Home: hero carousel, "Sent to you", "Your Blends", a separate Spotify module.
- A new landing page as a scroll story.
- The Room, Taste Constellation, recap story and podium with real covers.
