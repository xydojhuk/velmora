#!/usr/bin/env bash
set -euo pipefail
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then exec sudo bash "$0" "$@"; fi
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=/etc/velmora/velmora.env
BACKUP_DIR=/var/backups/velmora
[[ -f "$ENV_FILE" ]] || { echo "Velmora server bootstrap configuration was not found: $ENV_FILE"; exit 1; }
cd "$ROOT_DIR"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.yaml")
"${COMPOSE[@]}" ps installer >/dev/null

RUNTIME_ENV="$(docker run --rm --network none -v velmora_runtime_config:/cfg:ro alpine:3.22 cat /cfg/runtime.env 2>/dev/null || true)"
[[ -n "$RUNTIME_ENV" ]] || { echo "Velmora has not completed the browser installer yet."; exit 1; }
value(){ printf '%s\n' "$RUNTIME_ENV" | sed -n "s/^$1=//p" | head -n1; }
DB_HOST="$(value DATABASE_HOST)"; DB_PORT="$(value DATABASE_PORT)"; DB_USER="$(value DATABASE_USER)"; DB_NAME="$(value DATABASE_NAME)"; DB_SSLMODE="$(value DATABASE_SSLMODE)"
DB_PASSWORD="$(docker run --rm --network none -v velmora_runtime_secrets:/sec:ro alpine:3.22 cat /sec/database_password)"
[[ -n "$DB_HOST" && -n "$DB_USER" && -n "$DB_NAME" && -n "$DB_PASSWORD" ]] || { echo "Database runtime configuration is incomplete."; exit 1; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"; install -d -m 700 "$BACKUP_DIR"
DB_FILE="$BACKUP_DIR/velmora-db-${STAMP}.dump"; MEDIA_FILE="$BACKUP_DIR/velmora-media-${STAMP}.tar.gz"
NETWORK=velmora_edge; [[ "$DB_HOST" == "postgres" ]] && NETWORK=velmora_data
# Optional consistent snapshot: pause writes while pg_dump and media archive are captured.
# The cleanup trap restores ONLY services that were running before the backup.
QUIESCE="${1:-}"
[[ -z "$QUIESCE" || "$QUIESCE" == "--quiesce" ]] || { echo "Usage: $0 [--quiesce]" >&2; exit 2; }
resume_services() {
  if [[ "${#WAS_RUNNING[@]}" -gt 0 ]]; then "${COMPOSE[@]}" start "${WAS_RUNNING[@]}" || echo "WARNING: restart services manually" >&2; fi
}
WAS_RUNNING=()
if [[ "$QUIESCE" == "--quiesce" ]]; then
  for svc in backend frontend; do
    [[ -n "$("${COMPOSE[@]}" ps -q "$svc")" ]] && WAS_RUNNING+=("$svc")
  done
  trap resume_services EXIT
  if [[ "${#WAS_RUNNING[@]}" -gt 0 ]]; then "${COMPOSE[@]}" stop "${WAS_RUNNING[@]}"; fi
fi


echo "Creating PostgreSQL backup..."
docker run --rm --network "$NETWORK" -e PGPASSWORD="$DB_PASSWORD" -e PGSSLMODE="${DB_SSLMODE:-prefer}" postgres:18.6-alpine \
  pg_dump -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER" -d "$DB_NAME" -Fc > "$DB_FILE"

echo "Creating media backup..."
docker run --rm --network none --read-only --cap-drop ALL -v velmora_media_data:/source:ro alpine:3.22 sh -c 'cd /source && tar -czf - .' > "$MEDIA_FILE"
chmod 600 "$DB_FILE" "$MEDIA_FILE"
[[ -s "$DB_FILE" && -s "$MEDIA_FILE" ]] || { echo "Backup creation failed."; exit 1; }
VERSION="$(tr -d '\r\n' < "$ROOT_DIR/VERSION")"
META_FILE="$BACKUP_DIR/velmora-backup-${STAMP}.txt"
printf 'version=%s\ncreated_utc=%s\ndatabase=%s\nmedia=%s\n' "$VERSION" "$STAMP" "$(basename "$DB_FILE")" "$(basename "$MEDIA_FILE")" > "$META_FILE"
(cd "$BACKUP_DIR" && sha256sum "$(basename "$DB_FILE")" "$(basename "$MEDIA_FILE")") > "$BACKUP_DIR/velmora-db-${STAMP}.sha256"
chmod 600 "$META_FILE" "$BACKUP_DIR/velmora-db-${STAMP}.sha256"
echo "Backup created:"; echo "$DB_FILE"; echo "$MEDIA_FILE"
