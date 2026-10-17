#!/usr/bin/env bash
set -euo pipefail
[[ "${EUID:-$(id -u)}" -eq 0 ]] || exec sudo bash "$0" "$@"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=/etc/velmora/velmora.env
[[ -f "$ENV_FILE" ]] || { echo 'Production env not found' >&2; exit 1; }
cd "$ROOT_DIR"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.yaml")
"${COMPOSE[@]}" config -q
# Mandatory verified backup before rebuilding any image.
"$ROOT_DIR/scripts/backup.sh" --quiesce
for service in installer backend frontend; do
  container_id="$("${COMPOSE[@]}" ps -q "$service")"
  [[ -n "$container_id" ]] || { echo "No previous $service container; refusing unsafe upgrade" >&2; exit 1; }
  image_id="$(docker inspect --format '{{.Image}}' "$container_id")"
  docker tag "$image_id" "velmora-${service}:rollback"
done
"${COMPOSE[@]}" build --pull
"${COMPOSE[@]}" up -d --no-build
for service in installer backend frontend; do
  container_id="$("${COMPOSE[@]}" ps -q "$service")"
  for attempt in $(seq 1 40); do
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id" 2>/dev/null || true)"
    [[ "$health" == healthy ]] && break
    [[ "$health" == unhealthy || "$health" == exited ]] && break
    sleep 3
  done
  [[ "$health" == healthy ]] || { echo "Upgrade failed: $service=$health. Previous images: sudo ./velmora.sh rollback. DB backup: /var/backups/velmora" >&2; exit 1; }
done
"${COMPOSE[@]}" ps
echo "Containers healthy. Run production preflight and smoke tests before considering the update complete."
