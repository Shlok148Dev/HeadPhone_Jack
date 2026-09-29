# ADR-0006: One migration history (Django); ingest-ml writes the ingestion tables

- Status: Accepted
- Date: 2026-09-29

## Context
Technical Bible 1.1 says "Only core-api writes business tables" and "Only ingest-ml calls platform APIs"; 9.1 says tokens are "decrypted only inside ingest-ml". Linking a source both stores an encrypted token and calls the platform, so the rules collide.

## Decision
- Django owns all migrations.
- ingest-ml writes the ingestion-domain tables `platform_connections`, `linked_sources`, `scrobble_tokens`, `recordings`, `recording_links`, `artists` and `artist_tags` with SQLAlchemy Core. core-api only reads them.
- The web app never calls ingest-ml for user actions. It calls core-api `/api/v1/sources/*`, which proxies to ingest-ml `/internal/sources/*` with the service token. Only `/ingest/1/*` (scrobbler push) is public on ingest-ml.
- Celery lives in core-api's image (Technical Bible 1.1: workers run code from the service packages). Poll tasks call ingest-ml `/internal/poll/*`, so platform calls stay inside ingest-ml.
