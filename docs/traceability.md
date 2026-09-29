# Traceability: story → tests → files

Status: ✅ automated and passing · 🟡 partial · ⬜ not started. Updated at the end of each sprint.

| Story | Scenario / check | Tests | Implementation | Status |
| --- | --- | --- | --- | --- |
| JNG-01-01 | Sign up with email; 18+ gate; refresh rotation | `services/core_api/tests/accounts/*`; `apps/web/e2e/ep01/JNG-01-01.spec.ts` (adult sign-up, under-18 refused) | `accounts/auth_views.py`, `accounts/services.py`, `apps/web/src/app/signup`, `signin`, `lib/auth.tsx` | ✅ (Google: backend tested with mocks; button needs HA-3) |
| JNG-01-10 | Delete account; erasure reaches ingest | `tests/accounts/test_data_rights.py`, `tests/accounts/test_ingest_erasure.py`; ingest `test_delete_user_data_is_complete_and_idempotent` | `accounts/services.py`, `ingest_ml/api/internal.py` | ✅ (UI in S10) |
| JNG-01-12 | 4-step onboarding | — (E2E covers sources step landing) | `apps/web/src/app/onboarding/[step]` | 🟡 profile, sources, privacy built; friends step in S3 |
| JNG-01-13 | Push playing-now shows Live within seconds; unknown token rejected | `services/ingest_ml/tests/acceptance/test_JNG_01_13.py` (+ `features/ep01/JNG-01-13_push.feature`), `test_push_api.py` | `ingest_ml/api/push.py`, `ingest_ml/push/service.py` | ✅ |
| JNG-01-14 | One button per platform; Companion capture | `apps/companion-extension/tests/*` (74) | `apps/companion-extension`, `apps/web/src/components/app/Connect.tsx`, `app/connect/companion` | 🟡 browser route done; Spotify direct/Last.fm routes in S2 |
| JNG-05-01 | Apple Music only never LIVE; stale now-playing 120 s → "2 min ago"; no route in card | `services/core_api/tests/acceptance/*JNG_05_01*` (pytest-bdd); `apps/web/e2e/ep05/JNG-05-01.spec.ts` | `feed/resolver.py`, `jingle_common/labels.py`, `apps/web/src/app/(app)/home` | ✅ |
| JNG-05-08 | Empty state for no friends | `apps/web/e2e/screens.spec.ts` (screenshot) | `apps/web/src/app/(app)/home/page.tsx` | ✅ |
| JNG-02-05, 02-06 | Hide precise time; Private mode | `tests/accounts/test_privacy*`, resolver tests | `accounts/views.py`, `feed/resolver.py` | ✅ API (UI in S3) |
| BR-01 | No false Live | resolver tests; ingest NP TTL tests; extension staleness tests; simulator tests | `feed/resolver.py`, `push/service.py`, `companion-extension/src/background/scrobbler.ts` | ✅ |
| BR-03/04 | Lineage flags (`trainable`, `analytics_allowed`) | `packages/py-common/tests`, ingest `test_listen_doc_carries_lineage_flags` | `jingle_common/events.py`, `push/service.py` | ✅ |
| BR-14 | No route words in product | web E2E `ROUTE_WORDS` check; `jingle_common` label tests | labels, cards | ✅ |
| ADR-0010 | Demo world | `tests/accounts/test_seed_demo.py`, `tests/test_demo_simulator.py` | `seed_demo.py`, `ingest_ml/demo/simulator.py` | ✅ |
