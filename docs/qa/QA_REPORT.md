# Jingle full QA campaign: results and gaps (2026-10-02)

**Verdict:** this is not launch-ready for a public production launch yet, but it is ready for a closed pilot.
- The functional core is solid and well tested.
- The campaign found and fixed real defects:
  - throughput was 4.5× too low;
  - sign-in brute force was effectively unlimited;
  - a public API map;
  - pages scrolling sideways on phones;
  - a duplicate sign-in form;
  - missing profile photos;
  - songs that couldn't be found.
- Still open:
  - observability;
  - 15-minute recovery point;
  - zero-downtime deploys;
  - Lighthouse-measured LCP;
  - a real 5,000-user test on production-sized hardware.

## 1. What was tested

| Type | How | Result |
| --- | --- | --- |
| Unit and white-box (backend) | pytest with coverage: core-api, ingest-ml | **340 + 169 passed**; coverage **92% / 86%** (NFR-OBS-05 ≥ 80% ✅) |
| Unit (realtime gateway) | vitest | 9 passed |
| Unit (web) | vitest with v8 coverage (plugin added this campaign) | 102 passed; **coverage 11%** of statements (see gap G-9) |
| Functional and regression (black-box E2E) | Playwright, every epic's Gherkin scenarios | 40 passed; 1 regression found and fixed (duplicate sign-in form) |
| Accessibility | axe WCAG 2.2 AA on every route, both themes; keyboard; Lighthouse a11y | 0 violations; Lighthouse a11y **100** on landing and sign-in |
| Product audit (new, `e2e/qa-audit.spec.ts`) | 22 routes × 3 widths × 2 themes = 132 page loads. Checks: console/page errors, failed requests, broken or blurry images, sideways scroll, tap targets, placeholder text, heading structure, load time | 0 console errors, failed requests, broken/blurry images or placeholder text. **Found:** Home 495 px sideways scroll (phone/tablet), profile 71 px, staff page without h1, small drop-card links; all fixed |
| Load (smoke) | k6, 50 users, read mix | p95 **95 ms**, 0 errors ✅ |
| Stress and capacity (new, `infra/k6/stress.js`) | k6 ramp 50 → 300 users, reads and writes | See section 3: 59 → **388 req/s** after fixes |
| Performance (lab) | Lighthouse 12, mobile 4G, simulated and applied throttling; CDP field emulation | See section 4 |
| Security | Dependency audits (pnpm, pip-audit); secret scan; headers; probes (forged JWT, admin, internal routes, brute force, schema exposure, uploads) | Deps clean, no secrets, strong headers. **Found:** no effective sign-in lockout and a public API schema; both fixed |
| Database efficiency | Query counting per endpoint | Feed **63 → 14** queries, circles **45 → 27** |

## 2. Defects found and fixed in this campaign

| # | Severity | Defect | Fix |
| --- | --- | --- | --- |
| D1 | Critical | API served ~2 requests at a time: sync Django views on an ASGI server are serialised onto one thread per worker. 59 req/s ceiling, p95 12.6 s, 15% errors at 300 users | Gunicorn gthread (WSGI): 4–8 processes × 8 threads |
| D2 | Critical | `.env` and `.env.example` forced `DB_CONN_MAX_AGE=0`: a new Postgres connection (and process) per request; Postgres at 526% CPU | Persistent, health-checked connections (60 s) |
| D3 | High | N+1 queries: every friend on the feed cost friendship, block, privacy, link and artwork queries | `policy.bulk()`: one query per kind for the whole page |
| D4 | High | Sign-in brute force: local and template limit of 120 attempts/minute; production 10/min per IP+email ≈ 14k guesses/day | Per-account lockout after 20 failures/hour from any IP. Only failures count; hashed keys (no raw emails in Redis) |
| D5 | Medium | `/api/schema/docs/` public: a full map of the API | Staff-only unless `API_DOCS_PUBLIC` |
| D6 | High | No profile photos (`avatar_url` was always null) | Upload/replace/remove. Validated by content, re-encoded (EXIF/GPS stripped), square 512/128 px, 5 MB cap, bomb guard, purged with the account, served read-only by the edge |
| D7 | High | Song search only knew songs someone in Jingle had already played; new releases could not be dropped or sent | Apple catalogue fallback (~100M songs, exact Apple Music link), cached 24 h, within 80% of the API budget; tests run offline |
| D8 | High | Home scrolled 495 px sideways on phones and tablets (Drop shelf unconstrained) | Width constraints |
| D9 | Medium | Duplicate sign-in form on first render after deploy (`useSearchParams` client-render bailout + streaming) | Read `?next=` at use time; no bailout |
| D10 | Medium | Live equaliser animated SVG `<rect>`s: not compositable, ~800 ms of main thread per 6 s on the landing page | HTML bars on the compositor (layout −81%) |
| D11 | Medium | Entrance animations started at opacity 0, so Chrome ignored the hero as an LCP candidate | Transform-only entrances |
| D12 | Low | No favicon (404 on every page) | `app/icon.svg` from the Jingle mark |
| D13 | Low | Profile `sr-only` table overflowed (tables ignore sr-only sizing) | Hide a wrapper |
| D14 | Low | Settings had no way to edit name, college or city after onboarding | Profile editor in Settings → Account |
| D15 | Test-infra | A song-search test called Apple's real API | Catalogue disabled under tests; opt-in mocks |

## 3. Load and capacity (laptop: 12 cores, 7.4 GB for Docker, all 12 services plus k6 on one machine)

| Configuration | Throughput | p95 at 300 users | Errors (excluding rate limits) |
| --- | --- | --- | --- |
| Before (ASGI, 2 workers, no conn reuse, N+1) | 59 req/s | 12.6 s | 15% |
| WSGI threads | 149 req/s | 1.9 s | 0 |
| + query batching + connection reuse | 265 req/s | 1.15 s | 0 |
| + 8 processes | **388 req/s** | ~0.6 s at 150 users | 0 |

- **At 50 users:** p95 95 ms.
- **At 100 users of the aggressive mix:** p95 389 ms.
- **The bottleneck is now Python CPU in the API.** It scales by adding processes or servers (NFR-SCAL-04 behaviour observed: +48% from 4 → 8 processes).
- **NFR-SCAL-01/02 (5,000 users, 1,000 req/s) can't be proven on a laptop.** `infra/k6/scale-5000.js` is ready for a staging stack (see `docs/runbooks/scale-test.md`).

## 4. Page performance (NFR-PERF-06: LCP ≤ 2.5 s on mobile 4G)

| Page | Lighthouse (simulated) | Lighthouse (applied) | CDP field emulation (4G, 4× CPU) |
| --- | --- | --- | --- |
| Landing | LCP 4.7 s, perf 73 | LCP 3.3 s | **1.4 s** ✅ |
| Sign-in | LCP 5.5 s, perf 77 | LCP 3.9 s | **0.9 s** ✅ |

On every page in both modes: CLS ≈ 0, accessibility 100, SEO 100, best practices 96.

This is **not met as written** (the NFR names Lighthouse CI). Lab runs on a contended laptop vary ±20 points. The next levers are G-5.

## 5. NFR compliance matrix

| NFR | Status | Evidence |
| --- | --- | --- |
| PERF-01 reads p95 ≤ 300 ms, p99 ≤ 800 ms at peak | 🟡 Met to ~80 heavy users on a laptop; peak not defined on prod hardware | §3 |
| PERF-02 writes p95 ≤ 500 ms | 🟡 Same as PERF-01 (366 ms at 100 users) | §3 |
| PERF-03 feed for 200 friends ≤ 500 ms | 🟡 Batched; not measured at 200 friends | §2 D3 |
| PERF-04 WebSocket fan-out ≤ 1 s | 🟡 Earlier session-storm script; not re-run this campaign | `infra/k6/session-storm.js` |
| PERF-05 Live visible ≤ 60 s | ✅ Realtime push plus 90 s Live rule; E2E | ep05 |
| PERF-06 LCP ≤ 2.5 s (Lighthouse CI) | ❌ Lab 3.3–5.5 s; field emulation 0.9–1.4 s | §4 |
| PERF-07 Takeout 50 MB ≤ 30 s | ⚪ Not exercised this campaign | — |
| PERF-08 suggestions ≤ 200 ms | ✅ Precomputed, ~35 ms single request | §1 |
| SCAL-01/02 5,000 users / 1,000 rps | ⚪ Not provable on a laptop | §3 |
| SCAL-03 20k events/min | ⚪ Not measured | — |
| SCAL-04 horizontal scaling | ✅ Observed +48% from 4→8 processes | §3 |
| SCAL-05 2× headroom | ⚪ Needs prod metrics | — |
| SCAL-06 ≤ 80% of source budgets | ✅ Token buckets per source; catalogue 16/min of ~20 | code + tests |
| AVAIL-01 99.5% | ⚪ Single server, no HA; not measurable locally | — |
| AVAIL-02 RPO 15 min / RTO 1 h | ❌ Backups are daily (RPO 24 h); restore is tested weekly | `infra/backup` |
| AVAIL-03 source outage degrades only its cards | ✅ Degraded state with true time | ep05, tests |
| AVAIL-04 backoff + jitter + Retry-After, ≤ 3 tries | ✅ | `adapters/common.py` |
| AVAIL-05 zero-downtime deploys | ❌ `docker compose up` recreates containers | — |
| SEC-01 AES-256-GCM tokens, KMS key | 🟡 AES-256-GCM ✅; key in env, not a KMS | ingest settings |
| SEC-02 ASVS L2 auth/session/access | 🟡 Lockout added; no MFA; no formal ASVS audit | §2 D4 |
| SEC-03 cookies HttpOnly/Secure/Lax; 15-min access | ✅ (Secure outside local) | headers, settings |
| SEC-04 rate limits auth/search/requests/reports | ✅ After D4 | tests |
| SEC-05 WebSocket membership re-check | ✅ | realtime tests |
| SEC-06 dependency scans block criticals in CI | ✅ CI audits; scans clean today | `ci.yml` |
| SEC-07 uploads scanned in an isolated worker, deleted ≤ 24 h | 🟡 Avatars parsed in-process with strict limits; no AV scan | §2 D6 |
| PRIV-01 itemised, withdrawable consent | ✅ | settings/privacy, tests |
| PRIV-02 18+ until parental flow | ✅ Age gate | tests |
| PRIV-03 deletion ≤ 30 days; Spotify ≤ 24 h | ✅ Purge tasks (now incl. photos) | tests |
| PRIV-04 breach reporting ≤ 72 h | 🟡 Runbook process only | `docs/runbooks` |
| PRIV-05 hashed contact matching | ⚪ Contact matching not built | — |
| PRIV-06 export as JSON | ✅ | data-rights tests |
| PRIV-07 branding/credits | ✅ Spotify attribution; Last.fm/ListenBrainz credits; official marks (HA-UX-1 guideline check pending) | — |
| A11Y-01 0 automated WCAG 2.2 AA failures | ✅ (manual screen-reader pass not done) | axe suite |
| A11Y-02 contrast ≥ 4.5:1, focus visible | ✅ | tests, audit |
| A11Y-03 reduced motion | ✅ | CSS + tests |
| A11Y-04 populated feed in ≤ 5 min (usability) | ⚪ Needs real participants | — |
| OBS-01 trace IDs across all services (OpenTelemetry) | ❌ Request IDs only; no OpenTelemetry | — |
| OBS-02 dashboards + alerts at 80% budget | ❌ No metrics or alerting stack | — |
| OBS-03 false-Live > 0 pages on-call | ❌ No alerting | — |
| OBS-04 structured JSON logs, no tokens/emails | ✅ | logs |
| OBS-05 ≥ 80% backend coverage; adapter contract tests | ✅ 92% / 86% | §1 |

Legend: ✅ met · 🟡 partly or not at peak · ❌ not met · ⚪ not verifiable here.

## 6. Where the software lacks (ranked)

1. **G-1 Observability (OBS-01/02/03).** No OpenTelemetry, metrics, dashboards or alerting. A false-Live bug or an outage would go unnoticed. *Blocker for public launch.*
2. **G-2 Recovery (AVAIL-02/05).** Daily backups only; deploys cause downtime. Needs WAL archiving/PITR (or managed Postgres) and rolling deploys.
3. **G-3 Proven scale (SCAL-01/02).** Run `scale-5000.js` on a staging box sized per the runbook; tune `WEB_CONCURRENCY`, add PgBouncer.
4. **G-4 Catalogue depth across all four apps.** Search now covers Apple's catalogue with exact Apple Music links. Exact Spotify, YouTube Music and Amazon Music links are still searches ("Find in …"); exact matching needs each platform's catalogue API or a matcher (Odesli) after a terms review. Artist pages and album pages don't exist yet.
5. **G-5 Lab LCP (PERF-06).** Trim fonts (3 families, several weights) on auth and landing pages, lighten the grain layer, and set up Lighthouse CI on a quiet runner.
6. **G-6 Security depth.** KMS-managed keys, MFA/passkeys, a formal ASVS L2 review, and malware scanning for uploads.
7. **G-7 Product depth (the "it feels stock" gap).** Real users bring real avatars and real music. The demo data (personas, generated listening) still reads as staged. Missing for a top-tier social product:
   - artist and album pages;
   - drop reactions and "played it";
   - contact sync (PRIV-05 flow);
   - push notifications for drops;
   - onboarding that imports real listening history within minutes (A11Y-04 usability goal).
8. **G-8 Manual quality gates.** No screen-reader pass (A11Y-01 manual), no usability test with 10 people (A11Y-04), no exploratory test by a human on real phones.
9. **G-9 Web unit coverage 11%.** UI logic is covered mostly end-to-end. Component tests for NowStage, DailyDrop, AvatarUploader and Tune-in labelling would catch regressions earlier and faster.

## 7. How to re-run

```bash
# backend, with coverage
cd services/core_api && uv run pytest --cov=.
# web unit, with coverage
cd apps/web && npx vitest run --coverage
# E2E + a11y (stack up)
cd apps/web && npx playwright test
# product audit (132 page loads) → artifacts/qa/audit.jsonl
cd apps/web && QA_AUDIT=1 npx playwright test e2e/qa-audit.spec.ts
# load: smoke, stress ramp, or a flat level
docker run --rm -i --network jingle_default -v "$PWD/infra/k6:/k6" grafana/k6 run /k6/stress.js
docker run --rm -i --network jingle_default -e VUS=150 -v "$PWD/infra/k6:/k6" grafana/k6 run /k6/stress.js
```
