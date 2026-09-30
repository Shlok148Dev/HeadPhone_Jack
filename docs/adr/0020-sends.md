# ADR-0020: Sends, mixtapes and delivery status (Sprint 7)

- Status: Accepted
- Date: 2026-09-30

## Decisions
1. **Tables as Technical Bible 3.1** (`recommendations`, `recommendation_items`, `recommendation_deliveries`). A delivery row per recipient carries `delivered_at`, `viewed_at`, `played_at`, a reaction and the discovery credit. A reply with a song is a new recommendation with `reply_to` → the delivery it answers, sent only to the original sender.
2. **Items may be unresolved.** `recording_id` is nullable. The item keeps the title and artist the sender shared (a send is a user message). We never store artwork, IDs or other data from Spotify's API on a send. Links are resolved at read time from `recording_links`, with a search on each platform as the fallback (JNG-06-03).
3. **Recipients:** friends (BR-06) and members of circles the sender belongs to. Blocks in either direction are removed at send time and hidden at read time (BR-07). There are at most 50 recipients and 200 sends a day per user.
4. **Honest statuses.**
   - *Sent* means the row exists.
   - *Delivered* means the recipient's app fetched it (inbox or badge).
   - *Viewed* means the row was on screen, or the recipient reacted.
   - *Played* means one of the recipient's **own** listens matched the song (by recording or by normalised artist|title) at or after the send, within 30 days.
   - Only listens with `analytics_allowed` count, so direct-Spotify API data never becomes a stored fact (BR-03). Nothing is inferred from the sender's side.
5. **Discovery credit (Technical Bible 6.4)** runs daily at 04:30 on the default queue. It is granted when the sent artist is in the recipient's top 20 for the last 30 days, within 60 days of the send, and the artist was absent from the recipient's 6 months before the send.
6. **Song search** looks only at recordings already known to Jingle, meaning songs someone here has played. It makes no third-party search call and needs no keys (BR-15).
7. **Realtime:** a `notify` event goes to the recipient (`send`) and to the sender (`send_status`, `send_reaction`); the web app invalidates its inbox queries. There is no new socket event.
8. **Web budget:** the Send sheet and the Home suggestions shelf load lazily (`React.lazy`), so the Home first load stays at 180 kB.
