---
name: jingle-api-endpoint
description: How to add or change a Django REST Framework endpoint in Jingle's core-api — URL, serializer, permissions and block/friendship policy, error envelope, pagination, idempotency, OpenAPI schema via drf-spectacular, TypeScript client regeneration, and tests. Use this whenever you create or modify any /api/v1/ route, view, serializer, permission or queryset in services/core_api, even if it looks like a one-line change.
---

# Adding a core-api endpoint

The API is the contract with the web app (and later mobile). Consistency matters more than cleverness: every endpoint shares one error envelope, one pagination shape and one permission policy, so the client can be generated and every forbidden case behaves the same.

## Steps

1. **Find the story** (JNG-xx-yy) and its Gherkin in `docs/source/srs-v4.md`. Put the story ID in the view docstring.
2. **URL** under the app's `urls.py`, mounted at `/api/v1/`. Nouns, plural, kebab-free (`/friends/requests/{id}/accept`).
3. **Serializer**: explicit `fields`; never `__all__`. Output never includes `via`, tokens, emails of other users, or `birth_year`.
4. **Permissions**: `IsAuthenticated` by default. Object access goes through `core_api.policy` helpers (`can_view_activity(viewer, owner)`, `is_blocked_either_way(a, b)`, `is_circle_member(...)`). Blocks override everything (BR-07); activity visible only to accepted friends or shared circles (BR-06). Put these filters in querysets so lists and details agree.
5. **Errors**: raise `core_api.errors.ApiError(code="CIRCLE_FULL", message="This circle is full", status=409)`. The exception handler renders `{"error": {"code","message","details","request_id"}}`.
6. **Pagination**: list endpoints use `core_api.pagination.CursorPagination` → `{"results": [...], "next_cursor": ...}`, `limit` ≤ 100.
7. **Idempotency**: POSTs that create sends, votes, nominations or queue entries use the `@idempotent` decorator (stores response by `(user, Idempotency-Key)` in Redis 24 h).
8. **Rate limits** where NFR-SEC-04 applies (auth, search, friend requests 30/day, reports): `@ratelimit(key="user", rate=...)` from `core_api.ratelimit`.
9. **Schema**: annotate with `@extend_schema(...)` (request, responses incl. error codes, tags). Then regenerate:
   `docker compose exec core-api python manage.py spectacular --file /app/openapi.yaml` and `pnpm --filter @jingle/ts-client generate`.
10. **Events**: if other users should see the change live, publish to `events:domain` via `core_api.events.publish(...)`.
11. **Tests** (`services/core_api/tests/<app>/`): happy path, each Gherkin scenario (use `gherkin-to-tests`), unauthenticated 401, forbidden/blocked cases, validation errors, query-count assertion on lists (`django_assert_max_num_queries`), idempotent replay.
12. Run `uv run ruff check . && uv run pytest --cov` in `services/core_api`.
