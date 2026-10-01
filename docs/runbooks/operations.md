# Operations

All commands run from the repository root.

## Start, stop, status

```bash
docker compose up -d --build
```

```bash
docker compose ps
```

```bash
docker compose down
```

`docker compose down -v` also deletes all data volumes. Use it only on a laptop.

## Logs

The services log JSON lines. Tokens, passwords and secrets are never logged (S1/S11 reviews).

```bash
docker compose logs -f core-api workers ingest-ml realtime
```

## Migrations

core-api runs `migrate` on start. To run it by hand:

```bash
docker compose exec core-api python manage.py migrate
```

## Demo mode

`JINGLE_DEMO=1` seeds the demo world on every core-api start. The seed is idempotent, and it also resets the demo login's sandbox state: its pending requests and its suggestion dismissals.

| Login | Password | What |
| --- | --- | --- |
| `demo@jingle.local` | `jingle-demo-2026` | the demo member |
| `mod@jingle.local` | `jingle-demo-2026` | staff: `/staff` console |

## Staff tasks (in the app, `/staff`)

- **Reports.** Open reports with context. Each one can be dismissed, or answered with a warning, mute, suspension or ban, and every action needs a reason the person can see.
- **Appeals.** Uphold or overturn. Overturning lifts the action.
- **Audit log.** Every staff action is listed here.
- **Flags.** Turn features and sources on or off. Changes take effect within 30 seconds.
- **Budgets.** Per-source rate budgets and live usage, read from ingest-ml.
- **Spotify testers.** Up to 5 emails for the direct Spotify route. Emails in `.env` `SPOTIFY_ALLOWLIST` also count.

To make someone staff:

```bash
docker compose exec core-api python manage.py shell -c "from accounts.models import User; User.objects.filter(email='you@example.com').update(is_staff=True)"
```

Django's own `/admin` is deliberately **not** served by the edge, because it has no rate limiting or second factor. Use the staff console, or `manage.py shell` as above.

## Secrets

- `.env` is git-ignored. `.env.example` lists every variable.
- Outside `JINGLE_ENV=local`, core-api refuses to start with the example or weak values of `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY` and `SERVICE_TOKEN`.
- To rotate the JWT key, change `JWT_SIGNING_KEY` and restart core-api and realtime. Everyone signs in again.
- To rotate the token-encryption key, add the new KEK, set `TOKEN_KEK_ID`, and restart. Old tokens still decrypt with their recorded key id.
- To generate web push keys locally (no third party is involved), run:

```bash
cd services/core_api && uv run python -c "import base64;from cryptography.hazmat.primitives.asymmetric import ec;from cryptography.hazmat.primitives import serialization as s;k=ec.generate_private_key(ec.SECP256R1());b=lambda x:base64.urlsafe_b64encode(x).rstrip(b'=').decode();print('VAPID_PUBLIC_KEY='+b(k.public_key().public_bytes(s.Encoding.X962,s.PublicFormat.UncompressedPoint)));print('VAPID_PRIVATE_KEY='+b(k.private_numbers().private_value.to_bytes(32,'big')))"
```

## Scheduled jobs (Celery beat)

| Job | When |
| --- | --- |
| Source polling | every 10 s, adaptive by presence |
| Identity drain | every 60 s |
| Session sweep (host hand-over, idle rooms) | every 30 s |
| Sends: Played detection | every 60 s |
| Battle close | every 60 s |
| Discovery credits | daily 04:30 |
| Suggestions | nightly 03:00 |
| Suggested circles | Sunday 04:00 |
| Recaps | 1st and 2nd of the month, 06:00 |
| Compatibility recalibration | 1st of the month, 05:00 |

All times are IST.
