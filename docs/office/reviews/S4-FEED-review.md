# S4 Realtime + feed — combined review (Orchestrator: code, security, design checklists)

- Feed API: friends only (BR-06), blocks removed (BR-07), per-viewer privacy via `resolve_card`, BR-02 order (Live → newest Recent → Top → Hidden), Live filter, `degraded` when a friend's platform needs reconnecting (NFR-AVAIL-03), search fallback links (JNG-06-03), no `via` (BR-14). Single-card endpoint 404s for non-friends.
- Realtime (ADR-0018): JWT HS256 + issuer + `typ=access` checked on handshake; hints only (no track, route or time in payloads); per-pod stream consumption with `io.local`; rooms re-synced after friendship/block changes; presence + `watched:` keys drive adaptive polling (live only while someone is looking; recents every 15 min otherwise).
- Client: lazy socket.io (home 177 kB ≤ 180 kB budget), REST refetch on hint, reconnect banner, 60 s/15 s polling fallback, client-side Live guard at 90 s.
- Design fixes from screenshots: grid no longer duplicates Live friends ("Everyone else"); a friend with nothing captured reads "No plays yet", not "Hidden".
- A11y: checks run on settled UI (entry animation fade caused transient contrast readings).
- Tests: core-api feed 7 + full suite green; realtime 7; ingest adaptive polling; web unit 96; E2E 10 incl. JNG-05-02 live update without refresh.

VERDICT: APPROVED
