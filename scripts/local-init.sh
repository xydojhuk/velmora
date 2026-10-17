#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
umask 077

[[ -f .env.local ]] || cp .env.local.example .env.local

set_env() {
  local key="$1" value="$2" tmp
  tmp="$(mktemp)"
  awk -v key="$key" -v value="$value" '
    BEGIN { done=0 }
    $0 ~ "^" key "=" { if (!done) { print key "=" value; done=1 }; next }
    { print }
    END { if (!done) print key "=" value }
  ' .env.local > "$tmp"
  mv "$tmp" .env.local
}

get_env() {
  local key="$1"
  awk -F= -v key="$key" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' .env.local
}

random_token() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "$1"
  else
    od -An -N "$1" -tx1 /dev/urandom | tr -d ' \n'
    echo
  fi
}

set_env DOMAIN velmora.local
set_env ACME_EMAIL dev@velmora.local
set_env VELMORA_SITE_URL http://velmora.local
set_env VELMORA_BOOTSTRAP_MODE local
set_env VELMORA_BOOTSTRAP_DIR ./.bootstrap
set_env VELMORA_BOOTSTRAP_PG_SECRET_FILE ./.bootstrap/postgres_bootstrap_password

mkdir -p .bootstrap
chmod 700 .bootstrap

# Keep legacy files for server-parity/debugging, but local containers no longer
# need to traverse this host directory. This makes rootless Docker reliable.
[[ -s .bootstrap/postgres_bootstrap_password ]] || random_token 32 > .bootstrap/postgres_bootstrap_password
if [[ ! -f .bootstrap/installed.lock ]]; then
  [[ -s .bootstrap/setup_token ]] || random_token 12 > .bootstrap/setup_token
fi
chmod 600 .bootstrap/* 2>/dev/null || true

pg_password="$(get_env VELMORA_LOCAL_PG_BOOTSTRAP_PASSWORD || true)"
if [[ -z "$pg_password" ]]; then
  pg_password="$(cat .bootstrap/postgres_bootstrap_password)"
  set_env VELMORA_LOCAL_PG_BOOTSTRAP_PASSWORD "$pg_password"
fi

setup_token="$(get_env VELMORA_LOCAL_SETUP_TOKEN || true)"
if [[ ! -f .bootstrap/installed.lock && -z "$setup_token" ]]; then
  setup_token="$(cat .bootstrap/setup_token)"
  set_env VELMORA_LOCAL_SETUP_TOKEN "$setup_token"
fi

chmod 600 .env.local

if command -v selinuxenabled >/dev/null 2>&1 && selinuxenabled && command -v chcon >/dev/null 2>&1; then
  chcon -Rt container_file_t .bootstrap 2>/dev/null || true
fi

echo "Local bootstrap is ready."
echo "Add to /etc/hosts: 127.0.0.1 velmora.local"
if [[ ! -f .bootstrap/installed.lock && -n "${setup_token:-}" ]]; then
  echo "Setup code: $setup_token"
else
  echo "Setup code: <already consumed>"
fi
