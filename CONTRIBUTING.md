# Contributing to Jingle

Jingle is proprietary (see [LICENSE](LICENSE)). Contributions are by invitation from the
maintainer. If you've been invited, this is how we work.

## Ground rules

- **No false Live.** "Live" only when a real now-playing signal is under 90 seconds old.
- **No scraping, no unofficial APIs.** Only official, documented platform APIs.
- **Spotify data:** display-only, attributed, never used for ML, deleted within 24 h of unlinking.
- **Never commit secrets.** Use `.env` (ignored); add placeholders to `.env.example`. Never print
  secrets in logs. No production credentials in development or agent sessions.
- **Accessibility:** WCAG 2.2 AA for every screen.
- **Every change keeps the app runnable:** `docker compose up` must work.

## Workflow

1. Branch from `main`: `feat/<story-id>-short-name` or `fix/<short-name>`.
2. Commit with a clear message naming the story ID (e.g. `JNG-04-09: …`). Sign your commits
   (`git config commit.gpgsign true` or SSH signing) where possible.
3. Run the checks locally:
   - `pnpm -C apps/web lint && pnpm -C apps/web test`
   - `pytest` in `services/core_api` and `services/ingest_ml`
   - Playwright E2E against `docker compose up` (`pnpm -C apps/web exec playwright test`)
4. Open a pull request using the template. CI, CodeQL and secret scanning must pass, and the
   maintainer must approve before merge. Squash-merge into `main`.

Merging to `main` deploys to the live site automatically (see `docs/ops/DEPLOY.md`).

## Reporting bugs and ideas

Use the issue templates. Security problems go through [SECURITY.md](SECURITY.md), never a public issue.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
