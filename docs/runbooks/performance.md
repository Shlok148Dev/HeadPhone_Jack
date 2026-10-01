# Performance budgets and results

## Budgets

| What | Budget | Now (2026-10-01) |
| --- | --- | --- |
| API p95 under pilot load | ≤ 300 ms (SRS NFR-PERF) | **73 ms** overall, feed 62 ms (k6 smoke below) |
| Live update fan-out | ≤ 1 s p95 | measured seconds end to end in E2E (JNG-05-02); scale test pending |
| Home first-load JS | ≤ 180 kB | **180 kB** (circle chips, Send sheet and suggestions shelf lazy-loaded) |
| Other routes first-load JS | no budget yet; keep under 185 kB | 174–182 kB (`/friends` 182, `/blends` 181) |
| Live correctness | never Live over 90 s old (BR-01) | enforced server and client side, tested |

## k6 smoke: 50 concurrent users, local laptop stack

```bash
docker run --rm -i --network jingle_default -v "$PWD/infra/k6:/k6" grafana/k6 run /k6/smoke.js
```

Each user, in a loop: feed, me, notifications, inbox badge, friends, rituals, suggestions, then 5–10 s of think time. The socket keeps the feed live between page changes.

| Run | Requests | Errors | p95 overall | p95 feed | p95 slowest (suggestions) |
| --- | --- | --- | --- | --- | --- |
| Realistic think time (gate) | 5,321 | 0 % | **73 ms** | 62 ms | 81 ms |
| `STRESS=1` (1–3 s think, about 115 req/s offered) | 11,656 | 0 % | 371 ms | 360 ms | 404 ms |

Notes, stated honestly:
- The k6 users are fresh accounts with no friends, so their feeds are cheap. The demo member's 12-friend feed takes 162 ms unloaded. Feed cost grows with friends and is the first optimisation target at scale (per-owner signal cache).
- The laptop runs every service, the simulator and k6 together in Docker Desktop. The stress run is a capacity ceiling (about 80 req/s sustained with 0 errors on 4 uvicorn workers), not a pass/fail.

## What was tuned (S11)

| Change | Result |
| --- | --- |
| Threaded WSGI (gthread 3×8) | p95 500 ms. Worse than ASGI |
| Threaded WSGI + persistent DB connections | ran out of Postgres connections (18 % errors) |
| Final: uvicorn workers 2 → 4 (`WEB_CONCURRENCY`), `DB_CONN_MAX_AGE=0` | best of the configurations tried |
