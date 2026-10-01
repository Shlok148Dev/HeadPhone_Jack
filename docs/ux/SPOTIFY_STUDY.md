# What makes Spotify's web player work, and where Jingle beats it

These are principles, not pixels. Jingle copies none of Spotify's logo, fonts, icons, green, exact layouts or artwork treatments.

| Principle | What Spotify does | Jingle's version |
| --- | --- | --- |
| The shell | Library left, content centre, now-playing bottom, friend activity right; no page reloads | Same mental model: rail with Live now, centre feed, bottom bar with *my* track, right panel of *friends* with the Pulse and one-tap send back |
| Artwork first | Content recognised by cover before title | Real covers on every card, row, shelf, hero and story; nothing drawn on the art |
| Colour from content | Headers tinted from artwork | `ambient_dark/light` from the Artwork service, pre-checked for 4.5:1 text |
| Density | Many items per screen held together by rhythm | 4 px grid, 148–200 px cards, mono data labels, tight leading |
| Speed | Instant hovers, optimistic actions, no full-page loaders | Optimistic sends and votes, skeletons shaped like content, lazy-loaded heavy features, Home ≤ 180 kB |
| Context menus and shortcuts | Right-click everywhere, keyboard shortcuts | ⌘K palette across people, songs, circles and actions (context menus are on the list) |
| Calm motion | Small, quick, purposeful | 120–450 ms, springs for votes, nothing bouncy |

## Where Jingle is better, because Jingle is about people
1. **Presence you can read without words:** the Pulse (breathing coral = Live, still ring = recent). Spotify's friend feed is a text list with a tiny icon.
2. **Honesty:** Live only under 90 s, true times, "Sound comparison unavailable". Spotify never has to explain itself; Jingle shows its working.
3. **Shared moments:** the Room, the Sunday podium, the recap story, Blends with a reason on every track.
4. **Your app, not ours:** every track opens on the *viewer's* platform.

Self-scores against Spotify are in `review/SCORES.md`.
