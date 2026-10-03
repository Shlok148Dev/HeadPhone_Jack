#!/usr/bin/env bash
# One-time setup of the live server (Ubuntu 22.04/24.04, x86-64 or ARM64). Run ON the server:
#   bash bootstrap.sh <repo-ssh-url> <public-domain> <acme-email>
# Installs Docker, clones the repo with a read-only deploy key, writes .env with FRESH random
# secrets (generated here, never leaving the server), and starts Jingle behind HTTPS.
# Safe to re-run: it skips whatever is already done.
set -euo pipefail

REPO="${1:?repo ssh url, e.g. git@github.com:Shlok148Dev/HeadPhone_Jack.git}"
DOMAIN="${2:?public domain, e.g. 203-0-113-7.sslip.io}"
EMAIL="${3:?email for the HTTPS certificate}"

# 1. Docker
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
fi

# 2. Firewall: Oracle's Ubuntu image rejects everything but SSH in iptables.
for port in 80 443; do
  if ! sudo iptables -C INPUT -p tcp --dport "$port" -m state --state NEW -j ACCEPT 2>/dev/null; then
    sudo iptables -I INPUT 5 -p tcp --dport "$port" -m state --state NEW -j ACCEPT
  fi
done
if command -v netfilter-persistent >/dev/null; then sudo netfilter-persistent save >/dev/null; fi

# 3. Read-only deploy key (add the printed public key in GitHub -> Settings -> Deploy keys).
mkdir -p ~/.ssh && chmod 700 ~/.ssh
if [ ! -f ~/.ssh/jingle_deploy ]; then
  ssh-keygen -t ed25519 -N "" -C "jingle-server-deploy" -f ~/.ssh/jingle_deploy >/dev/null
  printf 'Host github.com\n  IdentityFile ~/.ssh/jingle_deploy\n  IdentitiesOnly yes\n' >> ~/.ssh/config
  ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
  echo
  echo "== Add this READ-ONLY deploy key to GitHub, then run this script again =="
  cat ~/.ssh/jingle_deploy.pub
  exit 0
fi

# 4. Code
[ -d ~/jingle ] || git clone "$REPO" ~/jingle
cd ~/jingle

# 5. Production .env with fresh secrets
if [ ! -f .env ]; then
  rnd() { python3 -c 'import secrets; print(secrets.token_urlsafe(48))'; }
  kek() { python3 -c 'import os, base64; print(base64.b64encode(os.urandom(32)).decode())'; }
  PGPW="$(python3 -c 'import secrets; print(secrets.token_hex(24))')"
  cp .env.example .env
  sed -i \
    -e "s|^JINGLE_ENV=.*|JINGLE_ENV=production|" \
    -e "s|^JINGLE_DEMO=.*|JINGLE_DEMO=0|" \
    -e "/^AUTH_[A-Z_]*_RATE=/d" \
    -e "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$(rnd)|" \
    -e "s|^JWT_SIGNING_KEY=.*|JWT_SIGNING_KEY=$(rnd)|" \
    -e "s|^SERVICE_TOKEN=.*|SERVICE_TOKEN=$(rnd)|" \
    -e "s|^TOKEN_KEK_B64=.*|TOKEN_KEK_B64=$(kek)|" \
    -e "s|^TOKEN_KEK_ID=.*|TOKEN_KEK_ID=prod-1|" \
    -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$PGPW|" \
    -e "s|^DATABASE_URL=postgres://jingle:[^@]*@|DATABASE_URL=postgres://jingle:$PGPW@|" \
    -e "s|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=https://$DOMAIN|" \
    -e "s|^VAPID_SUBJECT=.*|VAPID_SUBJECT=mailto:$EMAIL|" \
    .env
  printf '\nJINGLE_DOMAIN=%s\nJINGLE_ACME_EMAIL=%s\n' "$DOMAIN" "$EMAIL" >> .env
  chmod 600 .env
  echo "Wrote .env with fresh secrets (they stay on this server)."
fi

COMPOSE=(sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml)
"${COMPOSE[@]}" build

# 6. Web-push (VAPID) keys, generated once inside the API image
if ! grep -q '^VAPID_PRIVATE_KEY=.' .env; then
  KEYS="$("${COMPOSE[@]}" run --rm --no-deps -T core-api python - <<'PY'
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization as s
k = ec.generate_private_key(ec.SECP256R1())
b = lambda x: base64.urlsafe_b64encode(x).rstrip(b"=").decode()
print(b(k.public_key().public_bytes(s.Encoding.X962, s.PublicFormat.UncompressedPoint)))
print(b(k.private_numbers().private_value.to_bytes(32, "big")))
PY
)"
  PUB="$(printf '%s\n' "$KEYS" | tail -2 | head -1)"
  PRIV="$(printf '%s\n' "$KEYS" | tail -1)"
  sed -i -e "s|^VAPID_PUBLIC_KEY=.*|VAPID_PUBLIC_KEY=$PUB|" -e "s|^VAPID_PRIVATE_KEY=.*|VAPID_PRIVATE_KEY=$PRIV|" .env
fi

# 7. Start
"${COMPOSE[@]}" up -d
echo
echo "Jingle is starting at https://$DOMAIN (give it a minute for the HTTPS certificate)."
