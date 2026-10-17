#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  exec sudo bash "$0" "$@"
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=/etc/velmora/velmora.env
SECRET=/etc/velmora/secrets/smtp_password

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Velmora is not installed."
  exit 1
fi

read -r -s -p "SMTP password: " VALUE
echo

if [[ -z "$VALUE" ]]; then
  echo "Password cannot be empty."
  exit 1
fi

printf '%s' "$VALUE" > "$SECRET"

chown root:root "$SECRET"
chmod 644 "$SECRET"

docker compose \
  --env-file "$ENV_FILE" \
  -f "$ROOT_DIR/compose.yaml" \
  up -d --force-recreate backend

echo "SMTP password saved."