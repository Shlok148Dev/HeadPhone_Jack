# S3 Social graph — combined review (Orchestrator: code, security, design checklists)

- Rules in one place (`social/services.py`, `core_api/policy.py`): ordered-pair friendships (no duplicates, DB constraint), duplicate requests merge into one accepted friendship, 30 requests/day, recipient-only accept/decline, sender-only cancel.
- BR-07: blocks remove any friendship/request, hide both people from friends, requests, search and activity; requests to a blocker return the same 404 as a missing user; no notification is published for blocks.
- Privacy: "Only circles I choose" no longer lets plain friends see activity (fix); Private mode, exact-time toggle, discoverability via consent; blocked list with unblock.
- Reports (JNG-12-01) stored for the Sprint 10 moderation console; details capped at 1,000 chars; 20/day.
- Invite links: personal, rotatable, QR generated server-side (SVG from our own API), public preview shows first name only, accept requires sign-in; invite remembered across sign-up (sessionStorage).
- Tests: core-api social 12 (incl. Gherkin JNG-02-03/04), full suite green; E2E EP-02 (3) + earlier (6) green; screenshots dark/light × 1440/390 incl. friends, find, privacy, onboarding friends.

VERDICT: APPROVED
