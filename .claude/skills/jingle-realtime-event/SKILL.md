---
name: jingle-realtime-event
description: How to add or change a Socket.IO event or room in Jingle's realtime gateway (apps/realtime) and its web client hooks — handshake auth, room membership rules, forwarding state changes to core-api, versioned queue state, throttling, and tests. Use this whenever you touch apps/realtime, any socket.emit/socket.on in apps/web, live feed updates, presence, live sessions, votes or reconnect behaviour.
---

# Adding a realtime event

The gateway is fast because it is dumb: it authenticates sockets, keeps room membership, fans out events, and forwards anything that changes state to core-api, which owns the rules. That split is why realtime never writes PostgreSQL (ADR-0005) and why every state change re-checks membership (NFR-SEC-05).

## Steps

1. **Name** the event `noun:verb` (`vote:cast`, `queue:delta`). Add it to `apps/realtime/src/events.ts` (typed `ClientToServerEvents` / `ServerToClientEvents`) and to CONTRACTS.md §9.
2. **Auth**: the handshake middleware already verifies the access JWT (`jose`, HS256, `JWT_SIGNING_KEY`) and sets `socket.data.userId`. Never trust a user id from the payload.
3. **Rooms**: `user:{id}`, `friends:{id}`, `circle:{id}`, `session:{id}`. Joining a circle/session room calls core-api `/internal/rt/authorize` first; blocks (BR-07) deny.
4. **State changes** (`queue:add`, `vote:cast`, …): forward to core-api `POST /internal/rt/<action>` with `X-Service-Token` and the user id; core-api validates, writes, bumps the Redis version counter and publishes `queue.delta` to `events:domain`; the gateway's stream consumer emits it to the room. Ack the client with `{ok, error?}`.
5. **Ordering**: queue payloads include `version` (Redis `INCR`). Clients that see a gap emit `queue:sync` and receive `queue:state`.
6. **Back-pressure**: presence ≤ 1 per 10 s per user; feed updates coalesced per 2 s per room (`coalesce.ts`).
7. **Client**: add a typed hook in `apps/web/src/lib/realtime/` that updates TanStack Query caches (optimistic where the user acted).
8. **Tests**: Vitest in `apps/realtime/test/` with a real Socket.IO server + `socket.io-client`, mocked core-api (`msw` or a stub HTTP server) and `ioredis-mock`. Cover: unauthenticated rejected, non-member rejected, happy path fan-out, version gap → state resync.
