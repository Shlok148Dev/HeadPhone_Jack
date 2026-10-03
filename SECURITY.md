# Security policy

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Report privately through GitHub: **Security → Report a vulnerability** on this repository
(private vulnerability reporting), or email **shlok11@somaiya.edu** with "SECURITY" in the subject.

Include what you found, how to reproduce it, and the impact you expect. You'll get an
acknowledgement within 72 hours and a fix or plan within 14 days for confirmed issues.
Please give us a reasonable time to fix before disclosing.

## Scope

In scope: this repository's services (`apps/web`, `apps/realtime`, `apps/companion-extension`,
`apps/android`, `services/core_api`, `services/ingest_ml`), the deployment configuration and
the live deployment.

Out of scope: third-party services (Spotify, Apple, Google, Amazon, Last.fm), denial-of-service
and volumetric testing, social engineering, and findings that need a rooted device or a
compromised browser.

## How Jingle protects data

- Secrets live only in `.env` files that git ignores; `.env.example` holds placeholders.
  CI runs secret scanning on every push and pull request.
- Music-service tokens are sealed with AES-256-GCM before storage and never logged or returned.
- Spotify data is display-only, attributed, never used for ML, and deleted within 24 h of unlinking.
- Personal data follows India's DPDP Act: itemised, withdrawable consent, export and deletion.
- Dependencies are monitored by Dependabot; code is scanned by CodeQL.

## Supported versions

Only the `main` branch and the current live deployment receive security fixes.
