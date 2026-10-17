#!/usr/bin/env bash
set -euo pipefail
[[ "${EUID:-$(id -u)}" -eq 0 ]] || exec sudo bash "$0" "$@"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=/etc/velmora/velmora.env
[[ -f "$ENV_FILE" ]] || exit 1
if [[ "${1:-}" != "--apply" || "${2:-}" != "--confirm" || "${3:-}" != "ROLLBACK" ]]; then
  echo "DANGER: this restores the previous Docker images, NOT the previous database schema."
  echo "Use: sudo ./velmora.sh rollback --apply --confirm ROLLBACK"
  exit 0
fi
cd "$ROOT_DIR"
for service in installer backend frontend; do
  docker image inspect "velmora-${service}:rollback" >/dev/null || { echo "Missing previous image for $service" >&2; exit 1; }
done
for service in installer backend frontend; do
  docker tag "velmora-${service}:rollback" "velmora-${service}:latest"
done
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.yaml")
"${COMPOSE[@]}" up -d --no-build --force-recreate
"${COMPOSE[@]}" ps
echo "Previous images restored. Check schema compatibility and run preflight."
echo "If database migrations are incompatible, restore the PRE-UPDATE dump using restore.sh."
