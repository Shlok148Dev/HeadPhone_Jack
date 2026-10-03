#!/usr/bin/env bash
# One-time setup of the live server (Ubuntu 22.04/24.04, x86-64 or ARM64). Run ON the server:
#   bash bootstrap.sh <repo-ssh-url> <public-domain> <acme-email>
# Installs Docker, clones the repo with a read-only deploy key, writes .env with FRESH random
# secrets (generated here, never leaving the server), and starts Jingle behind HTTPS.
set -euo pipefail

REPO="${1:?repo ssh url, e.g. git@github.com:Shlok148Dev/HeadPhone_Jack.git}"
DOMAIN="${2:?public domain, e.g. 203-0-113-7.sslip.io}"
EMAIL="${3:?email for Let's Encrypt}"

if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
fi

# Read-only deploy key: add the printed public key in GitHub → Settings → Deploy keys.
if [ ! -f ~/.ssh/jingle_deploy ]; then
  ssh-keygen -t ed25519 -N "" -C "jingle-server-deploy" -f ~/.ssh/jingle_deploy >/dev/null
  printf 'Host github.com\n  IdentityFile ~/.ssh/jingle_deploy\n  IdentitiesOnly yes\n' >> ~/.ssh/config
  ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
  echo "== Add this READ-ONLY deploy key to the repo, then re-run this script =="
  cat ~/.ssh/jingle_deploy.pub
  exit 0
fi

[ -d ~/jingle ] || git clone "$REPO" ~/jingle
cd ~/jingle

if [ ! -f .env ]; then
  rnd() { python3 -c "import secrets;print(secrets.token_urlsafe(48))"; }
  kek() { python3 -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"; }
  cp .env.example .env
  sed -i \
    -e "s|^JINGLE_DEMO=.*|JINGLE_DEMO=0|" \
    -e "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$(rnd)|" \
    -e "s|^JWT_SIGNING_KEY=.*|JWT_SIGNING_KEY=$(rnd)|" \
    -e "s|^SERVICE_TOKEN=.*|SERVICE_TOKEN=$(rnd)|" \
    -e "s|^TOKEN_KEK_B64=.*|TOKEN_KEK_B64=$(kek)|" \
    -e "s|^TOKEN_KEK_ID=.*|TOKEN_KEK_ID=prod-1|" \
    -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(rnd)|" \
    -e "s|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=https://$DOMAIN|" \
    .env
  printf '\nJINGLE_DOMAIN=%s\nJINGLE_ACME_EMAIL=%s\n' "$DOMAIN" "$EMAIL" >> .env
  chmod 600 .env
  echo "Wrote .env with fresh secrets. Add your API keys (Last.fm, Spotify, Apple...) with: nano ~/jingle/.env"
fi

sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
echo "Jingle is starting at https://$DOMAIN (first build takes ~10 minutes)."
