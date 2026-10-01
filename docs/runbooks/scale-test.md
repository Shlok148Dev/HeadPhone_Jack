# Scale test: 1,000–5,000 concurrent users (JNG-13-01)

The scripts are written and parked for a staging environment. **The laptop pilot does not run them.**

| Script | Load | Pass |
| --- | --- | --- |
| `infra/k6/scale-5000.js` | ramp to 5,000 VUs over 10 min, hold 20 min; feed + badges with 5–15 s think | p95 ≤ 300 ms, errors < 0.5 % |
| `infra/k6/session-storm.js` | 100 sessions × 50 members voting (5,000 VUs) | vote p95 ≤ 1 s |
| plus | 5,000 sockets on realtime (Socket.IO load via `artillery-engine-socketio` or k6 `ws`) | fan-out p95 ≤ 1 s |

## Environment (Tech Bible §8)

- App: 3 core-api replicas (4 workers each), 3 realtime pods with the Redis adapter, 2 web, 2 ingest, workers split by queue.
- PgBouncer in transaction mode in front of PostgreSQL. Set `DB_CONN_MAX_AGE=0` (already the default).
- Managed PostgreSQL (4 vCPU / 16 GB), Redis (2 GB), MongoDB (time-series, 3-node).
- The edge, Caddy or a cloud load balancer, needs sticky sessions for `/rt`.

## Data prep

Registration is rate-limited, so create users and tokens with a management command run inside core-api (write it then; it is not shipped, so it can't be misused on the pilot). Shape:

- `users.json`: `[{"token": "...", "id": "..."}]`, with each user given 10–30 friends from the same pool so feeds are realistic.
- `rooms.json`: `[{"session_id", "entry_ids": [...], "members": [{"token"}]}]`.

## Run

```bash
k6 run -e BASE=https://staging.example.com -e USERS_FILE=users.json infra/k6/scale-5000.js
```

Watch the Grafana dashboards (NFR panels) and record results in this file.

## Expected first limits (Tech Bible §9)

1. PostgreSQL connections, fixed by PgBouncer.
2. Feed resolve cost per friend, fixed by caching each owner's resolved signal for 2–5 s; privacy is still applied per viewer.
3. Redis fan-out, fixed by moving domain events to NATS.
