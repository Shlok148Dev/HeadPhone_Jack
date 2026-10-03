# Live deployment on Oracle Cloud Always Free (auto-updates on every push to `main`)

Result: Jingle at `https://<your-ip-with-dashes>.sslip.io`, for example
`https://140-238-245-17.sslip.io`. It costs ₹0, uses real HTTPS, and redeploys itself on every
push to `main` that passes CI.

Why Oracle: Jingle needs Postgres, MongoDB, Redis, Qdrant, Celery workers and four app
services. Free PaaS tiers (Render, Vercel, Koyeb) can't run that set. Oracle's Always Free
Ampere A1 VM (up to 4 ARM cores, 24 GB RAM, 200 GB disk) runs it unchanged.

Time: about 45 minutes, most of it waiting for the first build.

---

## Step 1: Create the Oracle Cloud account (10 min)

1. Go to https://www.oracle.com/cloud/free/ and click **Start for free**.
2. Choose a **Home Region** close to your users, such as **India South (Hyderabad)** or
   **India West (Mumbai)**. You can't change it later, and Always Free servers only run in it.
3. Add a card for identity verification. Always Free resources are never charged. Oracle may
   place a small temporary hold.
4. Wait for the "account ready" email (usually minutes, sometimes a few hours).

## Step 2: Make an SSH key on your computer (2 min)

In PowerShell or Git Bash on your PC:

```bash
ssh-keygen -t ed25519 -f "$HOME/.ssh/oracle_jingle" -C "oracle-jingle"
```

Press Enter twice to skip the passphrase, or set one. This creates `oracle_jingle` (the
private key, which never leaves your PC) and `oracle_jingle.pub` (the public key).

## Step 3: Create the server (5 min)

1. In the Oracle console: **☰ → Compute → Instances → Create instance**.
2. **Name:** `jingle`.
3. **Image and shape → Edit:**
   - **Image:** Canonical **Ubuntu 24.04** (pick the normal one, not "Minimal").
   - **Shape:** Ampere → **VM.Standard.A1.Flex**, **4 OCPUs**, **24 GB** memory.
     It must show the "Always Free-eligible" label.
4. **Networking:** keep the defaults (new VCN, public subnet, **Assign a public IPv4 address = Yes**).
5. **Add SSH keys:** "Paste public keys" and paste the contents of `oracle_jingle.pub`. To view it:
   ```bash
   cat "$HOME/.ssh/oracle_jingle.pub"
   ```
6. **Boot volume:** you can set 100 GB; up to 200 GB total is free.
7. Click **Create**. When it shows **Running**, copy the **Public IP address**
   (for example `140.238.245.17`).

If you see "Out of capacity for shape VM.Standard.A1.Flex": try another Availability Domain in
the same form, try again later, or use 2 OCPUs and 12 GB.

## Step 4: Open ports 80 and 443 in Oracle's network (3 min)

1. On the instance page, click the **Subnet** link, then the **Default Security List**.
2. **Add Ingress Rules**, two rules:
   - Source CIDR `0.0.0.0/0`, IP protocol TCP, destination port `80`.
   - Source CIDR `0.0.0.0/0`, IP protocol TCP, destination port `443`.

The server's own firewall is opened by the setup script in step 7.

## Step 5: Your free HTTPS address

Take the public IP, replace the dots with dashes and add `.sslip.io`:

`140.238.245.17` → **`140-238-245-17.sslip.io`**

Nothing to register; sslip.io resolves that name to your IP. If you buy a domain later, point
its A record at the IP and use the domain instead.

## Step 6: Copy the setup script to the server (2 min)

From the repo folder on your PC (replace the IP):

```bash
scp -i "$HOME/.ssh/oracle_jingle" infra/deploy/bootstrap.sh ubuntu@140.238.245.17:~
```

Then log in:

```bash
ssh -i "$HOME/.ssh/oracle_jingle" ubuntu@140.238.245.17
```

## Step 7: Run the setup script (first run: about 2 min)

On the server:

```bash
bash bootstrap.sh git@github.com:Shlok148Dev/HeadPhone_Jack.git 140-238-245-17.sslip.io shlok11@somaiya.edu
```

The first run installs Docker, opens ports 80 and 443 in the server firewall, and prints a
**read-only deploy key** (one line starting with `ssh-ed25519`), then stops.

1. On GitHub: repo **Settings → Deploy keys → Add deploy key**.
2. Title `jingle-server`, paste the key, and leave **Allow write access unticked**. Save.

## Step 8: Run it again to build and start Jingle (15–25 min)

```bash
bash bootstrap.sh git@github.com:Shlok148Dev/HeadPhone_Jack.git 140-238-245-17.sslip.io shlok11@somaiya.edu
```

This run:
- clones the repo;
- writes `~/jingle/.env` with fresh secrets: Django key, JWT key, service token, token-encryption
  key, database password and web-push keys. They are generated on the server and never leave it;
- switches to production mode with no demo data;
- builds every image and starts everything behind HTTPS.

When it says "Jingle is starting", open **`https://140-238-245-17.sslip.io`**. The certificate
arrives on the first visit; give it about a minute.

Check the services are healthy:

```bash
cd ~/jingle && sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

## Step 9: Make yourself staff (1 min)

Sign up on the live site with your email, then on the server:

```bash
cd ~/jingle && sudo docker compose exec core-api python manage.py shell -c "from accounts.models import User; User.objects.filter(email='shlok11@somaiya.edu').update(is_staff=True)"
```

Use the email you signed up with. The staff console is at `/staff`.

## Step 10: Add your API keys (when you have them)

```bash
nano ~/jingle/.env
```

Fill in `LASTFM_API_KEY`, `LASTFM_SHARED_SECRET`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_ALLOWLIST`, the
`APPLE_MUSIC_*` values, `YOUTUBE_API_KEY` and so on. Save with Ctrl+O, Enter, then exit with Ctrl+X.
Then apply them:

```bash
cd ~/jingle && sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Set each platform's redirect URI to your live address:
- Spotify: `https://140-238-245-17.sslip.io/api/v1/sources/spotify/callback`
- Last.fm: `https://140-238-245-17.sslip.io/api/v1/sources/lastfm/callback`

Keys go only in the server's `.env`. Never put them in the repo, GitHub Actions logs or chat.

## Step 11: Auto-deploy on every push (10 min)

1. On your PC, make a separate key just for GitHub Actions:
   ```bash
   ssh-keygen -t ed25519 -f "$HOME/.ssh/jingle_ci" -N "" -C "github-actions-deploy"
   ```
2. Authorise it on the server. Run this from your PC; it uses your admin key from step 2:
   ```bash
   cat "$HOME/.ssh/jingle_ci.pub" | ssh -i "$HOME/.ssh/oracle_jingle" ubuntu@140.238.245.17 "cat >> ~/.ssh/authorized_keys"
   ```
3. Get the server's fingerprint line:
   ```bash
   ssh-keyscan 140.238.245.17
   ```
4. On GitHub: **Settings → Secrets and variables → Actions**.
   - **Secrets** tab → New repository secret, four times:

     | Name | Value |
     |---|---|
     | `DEPLOY_HOST` | `140.238.245.17` |
     | `DEPLOY_USER` | `ubuntu` |
     | `DEPLOY_SSH_KEY` | the whole contents of `jingle_ci` (the private key, including the BEGIN/END lines) |
     | `DEPLOY_KNOWN_HOSTS` | the output of step 3 |

   - **Variables** tab → New repository variable, twice:

     | Name | Value |
     |---|---|
     | `DEPLOY_ENABLED` | `true` |
     | `PUBLIC_URL` | `https://140-238-245-17.sslip.io` |
5. Delete the local `jingle_ci` private key once it's saved in GitHub; you won't need it again.
6. Test it: **Actions → deploy → Run workflow**. It should finish green with "Live: https://…".

From now on, **every push to `main` that passes CI goes live within minutes**. The deploy job
pulls that exact commit on the server and runs `docker compose up -d --build`; migrations run on start.

Optional: **Settings → Environments → production → Required reviewers** makes every deploy wait
for your approval.

## Step 12: Backups (before inviting real users)

On the server, run `crontab -e` and add:

```
30 2 * * * cd /home/ubuntu/jingle && infra/backup/backup.sh /var/backups/jingle >> /var/log/jingle-backup.log 2>&1
0 4 * * 0 cd /home/ubuntu/jingle && infra/backup/restore-test.sh /var/backups/jingle >> /var/log/jingle-backup.log 2>&1
```

Copy `/var/backups/jingle` off the server regularly. Oracle's free Object Storage (20 GB) with
`rclone` works.

## Everyday commands (on the server, in `~/jingle`)

| What | Command |
|---|---|
| Status | `sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml ps` |
| Logs (one service) | `sudo docker compose logs -f --tail=100 core-api` |
| Restart everything | `sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` |
| Free disk space | `sudo docker system prune -f` |

## Troubleshooting

- **Site doesn't load:**
  - Check both Oracle ingress rules (step 4).
  - Run `sudo iptables -L INPUT -n | head` and check that ports 80 and 443 show ACCEPT above any REJECT line.
- **Certificate error:**
  - The name must exactly match the server's IP, with dashes in place of dots.
  - Wait a minute, then check `sudo docker compose logs edge`.
- **Build fails with "no space left":** grow the boot volume in the Oracle console, or run `sudo docker system prune -af`.
- **Oracle reclaims an idle server:** only after 7 days of very low use. Real traffic prevents it, and upgrading the account to Pay As You Go stops it while keeping Always Free resources free.

See also [`deploy-pilot.md`](deploy-pilot.md), [`operations.md`](operations.md) and
[`backup-restore.md`](backup-restore.md).
