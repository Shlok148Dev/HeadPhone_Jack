# ADR-0012: One Celery app, five queues, in the core-api image

- Status: Accepted
- Date: 2026-09-29

The Celery app is `core_api.celery_app`, with queues `poll`, `ingest`, `ml`, `notify` and `default` (Technical Bible 7.4) and Beat schedules in Asia/Kolkata. For the pilot one worker container consumes all queues with concurrency 2; the Compose file documents how to split them. ML jobs import `jingle_ml` (a package inside `services/core_api/jingle_ml`) so the heavy libraries are installed only in the worker image target.
