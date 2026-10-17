#!/usr/bin/env bash
set -euo pipefail
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  command -v sudo >/dev/null 2>&1 || { echo "Root privileges are required."; exit 1; }
  exec sudo bash "$0" "$@"
fi
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR=/etc/velmora
BOOTSTRAP_DIR="$CONFIG_DIR/bootstrap"
ENV_FILE="$CONFIG_DIR/velmora.env"
cd "$ROOT_DIR"
umask 077

command -v docker >/dev/null 2>&1 || { echo "Docker Engine is required."; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 is required."; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker Engine is not running."; exit 1; }

install -d -m 700 "$CONFIG_DIR" "$BOOTSTRAP_DIR" /var/backups/velmora
random_token(){ openssl rand -hex "$1" 2>/dev/null || { od -An -N "$1" -tx1 /dev/urandom | tr -d ' \n'; echo; }; }
[[ -s "$BOOTSTRAP_DIR/postgres_bootstrap_password" ]] || random_token 32 > "$BOOTSTRAP_DIR/postgres_bootstrap_password"
NEW_BOOTSTRAP=0
if [[ ! -f "$ENV_FILE" ]]; then
  NEW_BOOTSTRAP=1
  [[ -s "$BOOTSTRAP_DIR/setup_token" ]] || random_token 12 > "$BOOTSTRAP_DIR/setup_token"
fi
chmod 600 "$BOOTSTRAP_DIR"/* 2>/dev/null || true

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Velmora server bootstrap"
  read -r -p "Domain without https://: " DOMAIN
  [[ "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ && "$DOMAIN" == *.* && "$DOMAIN" != *..* ]] || { echo "Invalid domain."; exit 1; }
  read -r -p "Email for Let's Encrypt: " ACME_EMAIL
  [[ "$ACME_EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}$ ]] || { echo "Invalid email."; exit 1; }
  cat > "$ENV_FILE" <<ENV
DOMAIN=$DOMAIN
ACME_EMAIL=$ACME_EMAIL
VELMORA_SITE_URL=https://$DOMAIN
VELMORA_BOOTSTRAP_MODE=server
VELMORA_BOOTSTRAP_DIR=$BOOTSTRAP_DIR
VELMORA_BOOTSTRAP_PG_SECRET_FILE=$BOOTSTRAP_DIR/postgres_bootstrap_password
GOOGLE_SITE_VERIFICATION=
BING_SITE_VERIFICATION=
YANDEX_SITE_VERIFICATION=
GOOGLE_ANALYTICS_ID=
GOOGLE_TAG_MANAGER_ID=
ENV
  chmod 600 "$ENV_FILE"
fi

set -a; source "$ENV_FILE"; set +a
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.yaml")
"${COMPOSE[@]}" config >/dev/null
"${COMPOSE[@]}" up -d --build

echo
echo "Velmora bootstrap started."
echo "Open: ${VELMORA_SITE_URL}/install"
echo "One-time setup code: $(cat "$BOOTSTRAP_DIR/setup_token" 2>/dev/null || echo '<already consumed>')"
echo
echo "Only server-level settings (domain/TLS) are configured here. Database, store and administrator settings are completed in the browser."
