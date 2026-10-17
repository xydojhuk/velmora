#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/_local-compose.sh"
cd "$ROOT_DIR"
printf 'This deletes the local database, media and installer state. Type RESET: '
read -r answer
[[ "$answer" == "RESET" ]] || { echo "Cancelled."; exit 1; }

# Bring the existing stack down before rotating bootstrap credentials.
if [[ -f .env.local ]]; then
  velmora_local_compose down -v --remove-orphans || true
else
  docker compose -f compose.yaml -f compose.local.yaml down -v --remove-orphans || true
fi

rm -rf .bootstrap
if [[ -f .env.local ]]; then
  tmp="$(mktemp)"
  awk '!/^VELMORA_LOCAL_SETUP_TOKEN=/ && !/^VELMORA_LOCAL_PG_BOOTSTRAP_PASSWORD=/' .env.local > "$tmp"
  mv "$tmp" .env.local
  chmod 600 .env.local
fi
./scripts/local-init.sh
echo "Local installation state reset with fresh bootstrap credentials. Run ./scripts/local-up.sh"
