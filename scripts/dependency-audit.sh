#!/usr/bin/env bash
set -euo pipefail
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  exec sudo bash "$0" "$@"
fi
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=/etc/velmora/velmora.env
cd "$ROOT_DIR"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.yaml")
echo "Python dependencies:"
"${COMPOSE[@]}" exec -T backend python -m pip check
echo
echo "npm production dependencies:"
"${COMPOSE[@]}" exec -T frontend npm audit --omit=dev --audit-level=high
