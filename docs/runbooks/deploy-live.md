# Live deployment that updates on every push to `main`

**Host: Oracle Cloud "Always Free" VM.** It's the best free option that runs all of Jingle
unchanged. Jingle needs Postgres, MongoDB, Redis, Qdrant, Celery workers and four app services.
Free PaaS tiers (Render, Koyeb, Vercel) can't run that set: no Mongo or Qdrant, no background
workers, and 512 MB limits. Oracle's Always Free Ampere A1 gives up to 4 ARM cores and 24 GB RAM at no cost.

How it works: CI passes on `main`, then the `deploy` workflow runs. It SSHes into the server,
checks out that exact commit and runs `docker compose … up -d --build`. Caddy serves HTTPS with a
free Let's Encrypt certificate.

## One-time setup (≈30 minutes; only you can do these steps)

1. **Create the server.**
   - Sign up at https://www.oracle.com/cloud/free/. A card is needed for verification; Always Free resources are never charged.
   - Create a Compute instance: **Ubuntu 24.04**, shape **VM.Standard.A1.Flex** (4 OCPU, 24 GB), and your SSH public key.
   - In the subnet's security list, allow inbound TCP **80** and **443**.
2. **Get a free HTTPS domain.**
   - Use `<public-ip-with-dashes>.sslip.io` (for example `203-0-113-7.sslip.io`). It needs no registration.
   - Or point your own domain's A record at the IP.
3. **Bootstrap the server.** SSH in, then run:
   ```bash
   curl -fsSLO https://raw.githubusercontent.com/Shlok148Dev/HeadPhone_Jack/main/infra/deploy/bootstrap.sh
   ```
   The repo is private, so if that URL fails, copy the script over with `scp` instead. Then run:
   ```bash
   bash bootstrap.sh git@github.com:Shlok148Dev/HeadPhone_Jack.git <domain> <your-email>
   ```
   - The first run prints a **read-only deploy key**. Add it in GitHub under **Settings → Deploy keys** with write access left off, then run the script again.
   - It writes `.env` with freshly generated secrets that stay on the server. Add your API keys afterwards with `nano ~/jingle/.env`.
   - Run `sudo ufw allow 80,443/tcp` if ufw is enabled. On Oracle's Ubuntu image, also open the iptables rules for 80 and 443.
4. **Create a CI deploy key** on your own computer:
   ```bash
   ssh-keygen -t ed25519 -f jingle_ci -N ""
   ```
   Append `jingle_ci.pub` to `~/.ssh/authorized_keys` on the server.
5. **Fill in the GitHub repository settings.**
   - Under **Settings → Secrets and variables → Actions → Secrets**, add:
     - `DEPLOY_HOST`: the server IP
     - `DEPLOY_USER`: `ubuntu`
     - `DEPLOY_SSH_KEY`: the contents of `jingle_ci` (the private key). Then delete your local copy.
     - `DEPLOY_KNOWN_HOSTS`: the output of `ssh-keyscan <server-ip>`
   - Under **Variables**, add:
     - `DEPLOY_ENABLED`: `true`
     - `PUBLIC_URL`: `https://<domain>`
   - Under **Settings → Environments → production**, you can optionally require your approval before each deploy.
6. **Update platform redirect URIs** (Spotify, Last.fm, Google) to `https://<domain>`, as in HA-1…3.

From now on every push to `main` that passes CI goes live within minutes. The run's summary
shows the URL. To redeploy by hand, use **Actions → deploy → Run workflow**.

## Notes

- **Demo world:** a public pilot runs with `JINGLE_DEMO=0`. For a showcase with seeded demo friends, set `JINGLE_DEMO=1` and `COMPOSE_PROFILES=demo` in the server `.env`.
- **Backups:** follow [`backup-restore.md`](backup-restore.md) and add the nightly cron.
- **Never put production secrets in the repository, Actions logs or chat.** The bootstrap script generates them on the server.
- See also [`deploy-pilot.md`](deploy-pilot.md) for staff accounts and first-run checks.
