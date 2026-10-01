# Deploy the pilot on one small server

The target is about 10 people. The same Compose stack runs everywhere: one machine, with TLS from Caddy.

## 1. Server

- 4 vCPU, 8 GB RAM, 80 GB SSD. Any provider works, for example a Hetzner CPX31 or a DigitalOcean 8 GB droplet.
- Ubuntu 24.04 LTS with Docker Engine and the Compose plugin.
- A domain or subdomain with an A record pointing at the server, for example `jingle.example.com`.
- Firewall: allow 22, 80 and 443 only. Nothing else is published, because the databases are internal to Compose.

## 2. Code and configuration

```bash
git clone <your repo> jingle && cd jingle && cp .env.example .env
```

Edit `.env`:

| Variable | Pilot value |
| --- | --- |
| `JINGLE_ENV` | `production` (strong secrets become mandatory) |
| `JINGLE_DEMO` | `0` |
| `PUBLIC_BASE_URL` | `https://jingle.example.com` |
| `JINGLE_DOMAIN` / `JINGLE_ACME_EMAIL` | your domain / your email (Let's Encrypt) |
| `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY`, `SERVICE_TOKEN` | each from `openssl rand -base64 48` |
| `POSTGRES_PASSWORD` and the matching `DATABASE_URL` | `openssl rand -base64 24` |
| Token KEK | see HUMAN_ACTIONS HA-4 |
| `VAPID_*` | generate per operations.md |
| `AUTH_*_RATE` | delete these lines to use the safe defaults |
| Spotify / Last.fm / Google | HUMAN_ACTIONS HA-1…3, with redirect URIs on your domain |

## 3. Start

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Caddy gets the certificate on first request. Then:

1. Open `https://jingle.example.com`, sign up, and make yourself staff (operations.md).
2. Add the 5 Spotify testers in `/staff` → Spotify testers.

## 4. Backups (required before inviting anyone)

```bash
crontab -e
```

Add:

```
30 2 * * * cd /home/ubuntu/jingle && infra/backup/backup.sh /var/backups/jingle >> /var/log/jingle-backup.log 2>&1
0 4 * * 0 cd /home/ubuntu/jingle && infra/backup/restore-test.sh /var/backups/jingle >> /var/log/jingle-backup.log 2>&1
```

Copy `/var/backups/jingle` off the server too, for example with `rclone` to any object store.

## 5. Updates

```bash
git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Migrations run on start.

The pilot accepts a few seconds of downtime per deploy. Zero-downtime deploys (JNG-13-05) need two app replicas behind the edge: see scale-test.md.

## 6. Invite the pilot

- Each person signs up, connects their music (Settings → Your music apps), and installs the Companion extension (README) for web players.
- Share invite links from Friends → Find.
