# ADR-0001: Phase 1 is a web-only, zero-approval pilot on one machine

- Status: Accepted
- Date: 2026-09-29
- Deciders: Orchestrator (kickoff §2 overrides all documents)

## Context
The SRS and Technical Bible target managed Kubernetes in an India region, Sign in with Apple, Apple Music as a launch path (SRS 4.3, PRD 7.1 "Already live") and mobile in R3. The kickoff brief (§2) was written later and overrides them.

## Decision
1. Web app only. No iOS/Android, no store work.
2. Nothing may depend on Apple Developer enrolment, Google verification, Amazon API access or any commercial agreement. The Apple Music (MusicKit), Amazon Music and Google Data Portability adapters are built fully but gated by flags `apple_music_enabled`, `amazon_music_enabled` and `google_dataportability_enabled`, all **off** by default.
3. Sign in with Apple (SRS JNG-01-01) is **deferred**: it needs Apple Developer enrolment. Email and Google only.
4. The full stack runs on one machine with Docker Compose (`docker-compose.yml` at the repo root). Kubernetes, Helm and Terraform are documented as the scale path, not built now.
5. The scaling architecture (stateless services, Socket.IO Redis adapter, per-source token buckets, PgBouncer-ready settings) is kept, so reaching 1,000–5,000 users needs configuration, not rewrites.

## Consequences
- SRS JNG-01-03 (Apple Music, Must) becomes "built, flagged off" for the pilot. Apple Music listeners are served by the Companion extension (Live on the web player) and show Recent otherwise.
- The pilot deploy guide targets one small VPS (`docs/runbooks/pilot-deployment.md`).

## Conflicts resolved
- SRS 2.4 (Kubernetes) vs kickoff §2: kickoff wins.
- PRD 7.1 "Apple Music: Already live" vs kickoff §2: flagged off.
