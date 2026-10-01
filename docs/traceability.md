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
| JNG-03-01/02/03 | ≤ 20 ranked suggestions, ≤ 3 reasons; friends of friends; taste twins | `tests/suggestions/test_suggestions.py` (pipeline, Adamic–Adar, twins cap); E2E `ep03/JNG-03.spec.ts` | `jingle_ml/suggest.py`, `jingle_ml/taste.py`, `suggestions/views.py` | ✅ |
| JNG-03-05/06 | Dismiss for 90 days; discoverability off excludes | Gherkin `features/ep03/JNG-03_suggestion_safety.feature`; `test_api_reads_cache_and_refilters` | `suggestions/views.py`, `jingle_ml/suggest.allowed` | ✅ |
| JNG-03-07 | Cold-start starter state and taste picker | `test_api_cold_start_and_taste` | `TastePicker`, `SuggestionsGrid`, `/me/taste` | ✅ |
| JNG-03-08 | Shared-context signal (sessions, battles, concerts) | `Graph.context` wired | `jingle_ml/suggest.py` | 🟡 fills in when those features ship (S6–S10) |
| JNG-05-01 | Apple Music only never LIVE; stale now-playing 120 s → "2 min ago"; no route in card | `services/core_api/tests/acceptance/*JNG_05_01*` (pytest-bdd); `apps/web/e2e/ep05/JNG-05-01.spec.ts` | `feed/resolver.py`, `jingle_common/labels.py`, `apps/web/src/app/(app)/home` | ✅ |
| JNG-05-02 | Live cards update without refreshing | E2E `ep05/JNG-05-02.spec.ts`; realtime `test/gateway.test.ts` | `apps/realtime/src/*`, `lib/realtime.tsx` | ✅ |
| JNG-05-03/06 | Live filter + Live now shelf + circle chips | `tests/feed/test_feed.py::test_JNG_05_06_live_filter`; `tests/circles/test_circles.py::test_JNG_04_04_circle_feed_and_circles_visibility`; E2E `ep04/JNG-04.spec.ts` (circle chip) | `feed/views.FeedView` (`?circle=`), Home chips | ✅ |
| JNG-04-01/08 | Create circle; ≤ 50 members; ≤ 20 per user | `test_JNG_04_01_create_and_limit_of_20`; Gherkin "Full circle"; E2E `ep04/JNG-04.spec.ts` | `circles/services.py`, `(app)/circles/page.tsx` | ✅ |
| JNG-04-02 | Invite friends + 7-day links; full circle message | `test_invites_only_friends_and_link_expiry`; Gherkin `features/ep04/JNG-04_circles.feature`; E2E link join | `circles/views.py`, `circles/join/[token]`, invite sheet | ✅ |
| JNG-04-03/06 | Roles; leave, remove, hand over | `test_JNG_04_03_roles_and_JNG_04_06_leave_remove_transfer`; E2E hand-over + leave | `circles/services.py`, `(app)/circles/[id]` | ✅ |
| JNG-04-04 | Circle feed; `share_circle` policy | `test_JNG_04_04_circle_feed_and_circles_visibility`, `test_block_hides_member_in_circle`, `test_non_members_cannot_see_circle` | `circles/views.CircleFeedView`, `core_api/policy.py` | ✅ |
| JNG-04-05 | Suggested circles (Leiden), never auto-join | Gherkin "Suggested circle is never auto-joined"; `test_leiden_names_and_skips_existing` | `jingle_ml/circles.py`, `jingle_ml/tasks.suggest_circles` | ✅ |
| JNG-04-07 | Circle settings (members can invite, battle schedule) | roles test (`members_can_invite`) | `CircleDetailView.patch`, Settings dialog | 🟡 schedule editor with battles (S10) |
| JNG-06-01 | Send a track to friends/circles with a ≤ 280 note | `tests/sends/test_sends.py::test_JNG_06_01_track_with_note_to_friends_only`, `test_send_to_circle_reaches_co_members_not_blocked`; E2E `ep06/JNG-06.spec.ts` | `sends/services.send`, `SendSheet` | ✅ |
| JNG-06-02 | Mixtape of 5–8 tracks | `test_JNG_06_02_mixtape_is_5_to_8`; E2E mixtape | `sends/services._items`, `SendSheet` | ✅ |
| JNG-06-03 | Opens on my own platform; "Not found on …" + search | Gherkin `features/ep06/JNG-06_sends.feature`; `apps/web/src/lib/sends.test.ts` | `sends/views.song`, `lib/sends.openTarget`, Inbox | ✅ |
| JNG-06-04 | Sent, Delivered, Viewed, Played | `test_JNG_06_04_statuses_and_JNG_06_07_inbox`, `test_played_ignores_listens_before_the_send`; E2E Sent tab | `sends/services.check_played`, `StatusChips` | ✅ |
| JNG-06-05 | Discovery credit | `test_JNG_06_05_discovery_credit`, `test_no_credit_when_artist_was_already_known` | `sends/services.discovery_credits` (daily) | ✅ |
| JNG-06-06 | React or reply with a track | `test_JNG_06_06_react_and_reply_with_a_song`; E2E react | `sends/services.react`, reply via `reply_to` | ✅ |
| JNG-06-07 | Inbox of received sends | `test_JNG_06_04_statuses_and_JNG_06_07_inbox`; E2E inbox | `sends/views.InboxView`, `(app)/inbox` | ✅ |
| JNG-07-01 | Blend with 2–6 friends or a circle | `tests/blends/test_blends.py` (engine + `test_JNG_07_01_02_…`, `test_blend_needs_friends_and_2_to_6_people`, `test_circle_blend_respects_circles_visibility`); E2E `ep07/JNG-07.spec.ts` | `blends/engine.py`, `blends/services.py`, `/blends` | ✅ |
| JNG-07-02 | One-line reason per track | `test_group_utility_prefers_shared_tracks_and_explains_them`, `test_reason_names_a_fan_of_the_artist` | `blends/engine.reason_for` | ✅ |
| JNG-07-03 | Regenerate keeps pins | `test_JNG_07_03_regenerate_keeps_pins`; E2E pin + regenerate | `blends/services.generate`, `/blends/[id]` | ✅ |
| JNG-07-04 | Save to my platform where allowed | `test_JNG_07_01_02_…` (`save.available` false + message) | `blends/views.SAVE_NOTE` | 🟡 honest "not available" until a zero-approval write path exists (ADR-0021) |
| JNG-07-05 | Start a session; invite friends or a circle | `test_JNG_07_05_start_and_invite_friends_or_circle`; E2E live room | `listening/services.start`, Blends "Listen together", circle page | ✅ |
| JNG-07-06 | Add to queue, optionally anonymously | `test_JNG_07_06_anonymous_add_hides_the_adder_and_is_idempotent`; E2E | `listening/services.add` | ✅ |
| JNG-07-07 | One vote per track; live re-order | Gherkin `features/ep07/JNG-07_live_queue.feature`; `test_JNG_07_07_…`; E2E 10 parallel votes (PostgreSQL) + live order | `listening/services.vote`, realtime `queue:delta`, `lib/live.applyDelta` | ✅ (p95 fan-out → k6 S11) |
| JNG-07-08 | Survives the host leaving | `test_JNG_07_08_survives_the_host_leaving`; E2E hand-over | `listening/services._hand_over`, `sweep` | ✅ |
| JNG-07-09 | Rejoin after a drop and see the current queue | Gherkin Reconnect; `apps/web/src/lib/live.test.ts` | `useSession` rejoin + refetch, versioned state | ✅ |
| JNG-08-01 | 0-100 compatibility with breakdown (BR-09) | Gherkin `features/ep08/JNG-08_explained_score.feature`; `tests/insights/test_insights.py`; E2E `ep08/JNG-08.spec.ts` | `insights/compute.py`, `insights/views.CompatibilityView`, `CompatibilityMeter`, `/u/[username]` | ✅ |
| JNG-08-02 | Shared artists, genres; sound only where available | Gherkin "Audio features unavailable" | `insights/compute.compatibility` | ✅ (sound unavailable in pilot, stated) |
| JNG-08-03 | 12-month taste timeline | `test_JNG_08_03_timeline_has_12_months`; E2E | `insights/compute.timeline`, profile Timeline | ✅ |
| JNG-08-06 | Analytics build over 2-4 weeks empty state | `test_JNG_08_06_new_member_sees_building_state` | `insights/compute.my_stats`, `MyInsights` | ✅ |
| JNG-08-07 | My stats: minutes, artists, genres, platforms | `test_JNG_08_07_my_stats`; E2E | `insights/compute.my_stats`, `/u/[username]` | ✅ |
| JNG-09-01/02 | Weekly battle: 1 nomination, 3 votes, not own; late vote refused | Gherkin `features/ep09/JNG-09_battle_integrity.feature`; `tests/rituals/test_rituals.py`; E2E `ep09/JNG-09-11-12.spec.ts` | `rituals/services.py`, `/rituals` | ✅ |
| JNG-09-03 | Leaderboard within 5 min of close | `test_JNG_09_03_results_published_by_close_job_with_notifications` | `rituals.tasks.close_due` (every minute), Podium | ✅ |
| JNG-09-04 | 8-week season table | `test_JNG_09_08_skip_week_and_JNG_09_04_season_ignores_it`; E2E | `rituals/services.season` | ✅ |
| JNG-09-05/06 | Monthly recap within 48 h; share as link or image | `test_JNG_09_05_recap_and_JNG_09_06_explicit_share`; E2E share/revoke | `rituals/services.make_recaps`, `RecapCard`, `/recap/[token]` | ✅ |
| JNG-09-08 | Skip a week without breaking the season | `test_JNG_09_08_…` | `rituals/services.skip_week` | ✅ |
| JNG-11-01 | In-app notifications | `tests/notifications/test_notifications.py::test_JNG_11_01_…`; E2E bell | `notifications/services.notify`, `/notifications` | ✅ |
| JNG-11-02 | Web push off until allowed | `test_JNG_11_02_push_only_after_opt_in`, `test_push_subscription_needs_vapid_and_https` | `public/sw.js`, `lib/trust.enablePush` | ✅ (real delivery manual) |
| JNG-11-03 | Per-type controls | `test_JNG_11_03_per_type_controls`; E2E | `/settings/notifications` | ✅ |
| JNG-11-04 | Quiet hours 23:00–08:00 local | `test_JNG_11_04_quiet_hours_span_midnight` | `notifications/services.in_quiet_hours` | ✅ |
| JNG-11-07 | ≤ 5 pushes a day | `test_JNG_11_07_five_pushes_a_day` | `notifications/services._push_budget` | ✅ |
| JNG-12-01 | Report a user, circle or note | `tests/moderation/test_moderation.py::test_JNG_12_01_…` | `social/views.ReportsView`, `moderation/context.py` | ✅ (comments: not built) |
| JNG-12-02/03 | Queue with context; warn/mute/suspend/ban with audit | `test_JNG_12_02_…`, `test_JNG_12_03_…`, `test_suspend_…`; E2E | `moderation/*`, `/staff` | ✅ |
| JNG-12-04 | Per-source budgets and live usage | `test_JNG_12_04_budgets_proxy_ingest`; ingest `test_ratelimit_usage.py` | ingest `/internal/budgets`, `/staff` Budgets | ✅ |
| JNG-12-05 | Feature flags per source and feature | `test_JNG_12_05_flags_toggle_is_audited` | `/staff` Flags | ✅ |
| JNG-12-06 | Spotify tester allowlist | `test_JNG_12_06_…` | `moderation.AllowlistEntry`, `sources/connect_views._allowlisted` | ✅ |
| JNG-12-08 | Appeal a moderation action | `test_JNG_12_08_overturned_appeal_lifts_the_action`; E2E | `/settings/account`, `/staff` Appeals | ✅ |
| JNG-13-01 | 5,000 concurrent users | k6 `infra/k6/smoke.js` (50 users, run: p95 73 ms, 0 errors); `scale-5000.js`, `session-storm.js` written | `docs/runbooks/performance.md`, `scale-test.md` | 🟡 scale run needs staging (documented) |
| JNG-13-02 | Dashboards and alerts per NFR | structured logs + health endpoints; panels listed | `docs/runbooks/scale-test.md` | 🟡 Grafana stack with the scale environment |
| JNG-13-03 | Daily backups, tested restore | `infra/backup/restore-test.sh` (run: counts match) | `infra/backup/*`, `docs/runbooks/backup-restore.md` | ✅ |
| JNG-13-04 | Download my data as JSON | `tests/accounts/test_data_rights_s11.py::test_export_covers_every_domain`; E2E `ep13/JNG-13.spec.ts` | `accounts/services.export_account`, Settings → Account | ✅ |
| JNG-01-10 | Delete my account (purge within 30 days, shared spaces handed over) | `test_deleting_an_owner_hands_shared_spaces_over`; E2E delete | `accounts/services.purge_account`, `hand_over_shared` | ✅ |
| JNG-13-05 | Zero-downtime deploys | — | `docs/runbooks/deploy-pilot.md` §5 | 🟡 pilot accepts seconds of downtime; needs 2 replicas |
| JNG-13-06 | Contract tests for every adapter | ingest-ml fixture contract tests (S2) | `services/ingest_ml/tests` | ✅ |
| JNG-13-07 | Screen reader and keyboard | E2E `a11y.spec.ts` (every route, both themes, axe WCAG 2.2 AA; skip link, focus visible) | all routes | ✅ |
| JNG-13-08 | Status page | `/healthz` per service | — | 🟡 not built (Should) |
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
