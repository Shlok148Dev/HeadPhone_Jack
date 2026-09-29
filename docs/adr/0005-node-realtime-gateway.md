# ADR-0005: Node + Socket.IO realtime gateway

- Status: Accepted (Technical Bible 1.3)
- Date: 2026-09-29

Realtime runs in `apps/realtime` (Node 22, Express, Socket.IO, `@socket.io/redis-adapter`, `jose`, `pino`). It never writes PostgreSQL. State-changing client events are forwarded to core-api `/internal/rt/*` with the service token, and core-api re-checks membership (NFR-SEC-05). The gateway consumes Redis Streams `events:listen` and `events:domain`. Django Channels remains the fallback (Technology Stack 3.4).
