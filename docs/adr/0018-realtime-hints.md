# ADR-0018: Realtime sends hints; cards are fetched over REST

- Status: Accepted
- Date: 2026-09-30

## Context
CONTRACTS §9 said `feed:update` carries a FeedCard. But a card depends on the viewer (blocks, "only circles I choose", Private mode, exact-time preference). Building cards in the gateway would duplicate core-api's policy in Node, against ADR-0005 (the gateway is dumb; core-api owns rules).

## Decision
- The gateway consumes `events:listen` and `events:domain` (XREAD per pod, emitting with `io.local` so the Redis adapter never duplicates), coalesces per user per 2 s, and emits **hints**: `feed:update {user_id}` to `friends:{user_id}`, `me:update` to `user:{id}`, `friends:changed` after friendship/block events (and re-joins both users' rooms), `notify {type,id}`.
- The client refetches `GET /api/v1/feed/{user_id}` (404 unless friends) and patches its cache; on reconnect it refetches the whole feed. REST polling (60 s, 15 s while disconnected) is the safety net.
- Presence: the gateway sets `presence:{me}` and `watched:{friend}` (TTL 120 s, heartbeat 60 s); the ingest poller polls live status only for active users and recents every 15 min otherwise (Technical Bible 2.3).
- `socket.io-client` loads after first paint to keep the home route within its JS budget.

## Consequences
One extra small REST call per hint per viewer: fine at pilot scale and cacheable later; privacy lives in exactly one place. CONTRACTS §9 updated.
