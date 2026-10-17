#!/usr/bin/env bash
set -euo pipefail
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  exec sudo bash "$0" "$@"
fi
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=/etc/velmora/velmora.env
cd "$ROOT_DIR"
read -r -p "Administrator email: " ADMIN_EMAIL
read -r -p "Administrator name: " ADMIN_NAME
docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.yaml" exec backend python -m app.cli create-admin --email "$ADMIN_EMAIL" --name "$ADMIN_NAME"
