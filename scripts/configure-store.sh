#!/usr/bin/env bash
set -euo pipefail
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  exec sudo bash "$0" "$@"
fi
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=/etc/velmora/velmora.env
cd "$ROOT_DIR"
read -r -p "Store name [Velmora]: " STORE_NAME
STORE_NAME=${STORE_NAME:-VELMORA}
read -r -p "Store phone: " STORE_PHONE
read -r -p "Store email: " STORE_EMAIL
read -r -p "Business hours: " STORE_HOURS
docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.yaml" exec -T backend python -m app.cli configure-store --name "$STORE_NAME" --phone "$STORE_PHONE" --email "$STORE_EMAIL" --hours "$STORE_HOURS"
