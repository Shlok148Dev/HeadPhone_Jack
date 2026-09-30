# Traceability: story → tests → files

Status: ✅ automated and passing · 🟡 partial · ⬜ not started. Updated at the end of each sprint.

| Story | Scenario / check | Tests | Implementation | Status |
| --- | --- | --- | --- | --- |
| JNG-01-01 | Sign up with email; 18+ gate; refresh rotation | `services/core_api/tests/accounts/*`; `apps/web/e2e/ep01/JNG-01-01.spec.ts` (adult sign-up, under-18 refused) | `accounts/auth_views.py`, `accounts/services.py`, `apps/web/src/app/signup`, `signin`, `lib/auth.tsx` | ✅ (Google: backend tested with mocks; button needs HA-3) |
| JNG-01-10 | Delete account; erasure reaches ingest | `tests/accounts/test_data_rights.py`, `tests/accounts/test_ingest_erasure.py`; ingest `test_delete_user_data_is_complete_and_idempotent` | `accounts/services.py`, `ingest_ml/api/internal.py` | ✅ (UI in S10) |
| JNG-01-02 | Valid ListenBrainz token links; invalid token exact copy, no record | ingest `tests/contract/test_sources.py::test_JNG_01_02_*`; core-api `tests/sources/test_connect.py::test_JNG_01_02_*` | `adapters/listenbrainz.py`, `orchestrator.py`, `sources/connect_views.py` | ✅ |
| JNG-01-03 | Apple Music (flagged) recent plays, never Live | `test_apple_music_recent_is_estimated_and_never_live`, `test_flagged_adapters_absent_while_flag_off` | `adapters/flagged.py` | ✅ built, flag off |
| JNG-01-04 | Allowlisted tester connects directly; non-allowlisted gets the bridge path; allowlist full falls back | `test_JNG_01_04_*`, `test_spotify_not_on_allowlist_falls_back`, `test_spotify_direct_is_display_only` | `adapters/spotify.py`, `orchestrator.py` | ✅ (fixtures; live needs HA-1) |
| JNG-01-05 | Spotify via Last.fm is Live on any device, never trains | `test_JNG_01_05_*`, `test_lastfm_route_needs_its_own_consent` | `adapters/lastfm.py` | ✅ (fixtures; live needs HA-2) |
| JNG-01-06 | Takeout JSON/HTML import, exports never Live | `test_takeout_*`, `test_JNG_01_06_import_endpoint`, E2E `JNG-01-14.spec.ts` | `takeout.py`, `api/connect.py`, Connect sheet | ✅ |
| JNG-01-07/08 | Google Data Portability, Amazon Music (flagged) | `test_flagged_adapters_absent_while_flag_off` | `adapters/flagged.py` | ✅ built, flag off |
| JNG-01-09 | Unlink one app, others keep working; Spotify data purged | `test_JNG_01_09_*`, core-api `test_JNG_01_09_unlink`, E2E disconnect | `orchestrator.unlink`, Settings | ✅ |
| JNG-01-11 | Re-consent state on 401 / private profile | `test_lastfm_private_profile_needs_reconnect` | `poller.py`, Settings row | ✅ (notification in S10) |
| JNG-01-12 | 4-step onboarding | E2E sign-up lands on sources; screenshots of all steps | `apps/web/src/app/onboarding/[step]` | ✅ |
| JNG-01-13 | Push playing-now shows Live within seconds; unknown token rejected | `services/ingest_ml/tests/acceptance/test_JNG_01_13.py` (+ `features/ep01/JNG-01-13_push.feature`), `test_push_api.py` | `ingest_ml/api/push.py`, `ingest_ml/push/service.py` | ✅ |
| JNG-01-14 | One button per platform; orchestrator picks the route; no route words on cards | extension tests (74); `test_JNG_01_04_route_choice`; core-api `test_JNG_01_14_*`; E2E `JNG-01-14.spec.ts` | `orchestrator.py`, `Connect.tsx`, `app/connect/companion` | ✅ |
| JNG-05-01 | Apple Music only never LIVE; stale now-playing 120 s → "2 min ago"; no route in card | `services/core_api/tests/acceptance/*JNG_05_01*` (pytest-bdd); `apps/web/e2e/ep05/JNG-05-01.spec.ts` | `feed/resolver.py`, `jingle_common/labels.py`, `apps/web/src/app/(app)/home` | ✅ |
| JNG-05-02 | Live cards update without refreshing | E2E `ep05/JNG-05-02.spec.ts`; realtime `test/gateway.test.ts` | `apps/realtime/src/*`, `lib/realtime.tsx` | ✅ |
| JNG-05-03/06 | Live filter + Live now shelf (circle chips in S6) | `tests/feed/test_feed.py::test_JNG_05_06_live_filter`; E2E | `feed/views.FeedView`, Home | ✅ (circles S6) |
| JNG-05-04 | Open in my own app (search fallback) | `test_JNG_05_04_search_links_for_open_in_my_app` | `feed/resolver._search_links`, `FeedCard.pickLink` | ✅ |
| JNG-05-07 | Source down → cached card, honest time, delayed | `test_JNG_05_07_needs_reconnect_marks_recent_as_delayed` | `feed/resolver._source_delayed`, Home degraded line | ✅ |
| JNG-05-08 | Empty state for no friends | `apps/web/e2e/screens.spec.ts` (screenshot) | `apps/web/src/app/(app)/home/page.tsx` | ✅ |
| JNG-02-01 | Search by username / display name | `tests/social/test_social.py::test_search_rules`; E2E `ep02/JNG-02.spec.ts` | `social/views.py`, `components/app/FindFriends.tsx` | ✅ |
| JNG-02-02 | Send/accept/decline/cancel; duplicate request merges | Gherkin `features/ep02/JNG-02-03_04_remove_block.feature` (Duplicate request); `test_request_accept_decline_cancel`; E2E | `social/services.py`, Friends page | ✅ |
| JNG-02-03 | Remove friend hides activity at once | `test_JNG_02_03_*`; E2E | `social/services.remove_friend`, `PersonMenu` | ✅ |
| JNG-02-04 | Block hides both ways, no notification | Gherkin (Blocking hides everything both ways) | `social/services.block`, `policy.py` | ✅ |
| JNG-02-05, 02-06 | Hide precise time; Private mode | `tests/accounts/test_privacy*`, resolver tests, `test_privacy_visibility_rules`; E2E privacy | `accounts/views.py`, `feed/resolver.py`, `settings/privacy` | ✅ |
| JNG-02-07 | Invite link + QR auto-sends a request | `test_JNG_02_07_*`; E2E invite/QR | `social/views.py`, `app/invite/[code]`, `lib/invite.ts` | ✅ |
| JNG-12-01 | Report a user | `test_JNG_12_01_report_user` | `social/views.ReportsView`, `PersonMenu` | ✅ (queue in S10) |
| BR-01 | No false Live | resolver tests; ingest NP TTL tests; extension staleness tests; simulator tests | `feed/resolver.py`, `push/service.py`, `companion-extension/src/background/scrobbler.ts` | ✅ |
| BR-03/04 | Lineage flags (`trainable`, `analytics_allowed`) | `packages/py-common/tests`, ingest `test_listen_doc_carries_lineage_flags` | `jingle_common/events.py`, `push/service.py` | ✅ |
| BR-14 | No route words in product | web E2E `ROUTE_WORDS` check; `jingle_common` label tests | labels, cards | ✅ |
| ADR-0010 | Demo world | `tests/accounts/test_seed_demo.py`, `tests/test_demo_simulator.py` | `seed_demo.py`, `ingest_ml/demo/simulator.py` | ✅ |
