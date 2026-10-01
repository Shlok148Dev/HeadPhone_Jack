# ADR-0024: UI font and artwork source (redesign R1)

- Status: Accepted
- Date: 2026-10-01

1. **UI font: Geist** replaces Inter. Inter is the most common UI face on the web, and the design brief and its audit tooling flag it as generic.
   - Geist reads crisply at 13–15 px in dense lists and has tabular numerals.
   - It is OFL-licensed and served by `next/font/google`, with no extra request.
   - Bricolage Grotesque (display) and JetBrains Mono (data) stay.
2. **Artwork source: Apple's public iTunes Search API**, server side, through a cached Artwork service.
   - It needs no key or approval, is official and open, and has high-resolution covers.
   - We store URLs and extracted colours, never images.
   - The MusicKit catalogue API replaces it once an Apple developer token exists (HA-UX-2).
