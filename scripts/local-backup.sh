#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
source "$ROOT_DIR/scripts/_local-compose.sh"
velmora_local_prepare "$ROOT_DIR"
velmora_local_compose ps installer >/dev/null
RUNTIME_ENV="$(docker run --rm --network none -v velmora_runtime_config:/cfg:ro alpine:3.22 cat /cfg/runtime.env)"
val(){ printf '%s\n' "$RUNTIME_ENV" | sed -n "s/^$1=//p" | head -n1; }
DB_HOST="$(val DATABASE_HOST)"; DB_PORT="$(val DATABASE_PORT)"; DB_USER="$(val DATABASE_USER)"; DB_NAME="$(val DATABASE_NAME)"; DB_SSLMODE="$(val DATABASE_SSLMODE)"
DB_PASSWORD="$(docker run --rm --network none -v velmora_runtime_secrets:/sec:ro alpine:3.22 cat /sec/database_password)"
[[ -n "$DB_HOST" && -n "$DB_USER" && -n "$DB_NAME" && -n "$DB_PASSWORD" ]] || exit 1
NETWORK=velmora_edge; [[ "$DB_HOST" == postgres ]] && NETWORK=velmora_data
# Optional consistent snapshot: pause writes while pg_dump and media archive are captured.
# The cleanup trap restores ONLY services that were running before the backup.
QUIESCE="${1:-}"
[[ -z "$QUIESCE" || "$QUIESCE" == "--quiesce" ]] || { echo "Usage: $0 [--quiesce]" >&2; exit 2; }
resume_services() {
  if [[ "${#WAS_RUNNING[@]}" -gt 0 ]]; then velmora_local_compose start "${WAS_RUNNING[@]}" || echo "WARNING: restart services manually" >&2; fi
}
WAS_RUNNING=()
if [[ "$QUIESCE" == "--quiesce" ]]; then
  for svc in backend frontend; do
    [[ -n "$(velmora_local_compose ps -q "$svc")" ]] && WAS_RUNNING+=("$svc")
  done
  trap resume_services EXIT
  if [[ "${#WAS_RUNNING[@]}" -gt 0 ]]; then velmora_local_compose stop "${WAS_RUNNING[@]}"; fi
fi

umask 077
OUT="$ROOT_DIR/.local/backups"; mkdir -p "$OUT"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DB_FILE="$OUT/velmora-db-${STAMP}.dump"; MEDIA_FILE="$OUT/velmora-media-${STAMP}.tar.gz"
docker run --rm --network "$NETWORK" -e PGPASSWORD="$DB_PASSWORD" -e PGSSLMODE="${DB_SSLMODE:-prefer}" postgres:18.6-alpine \
 pg_dump -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER" -d "$DB_NAME" -Fc > "$DB_FILE"
docker run --rm --network none -v velmora_media_data:/source:ro alpine:3.22 sh -c 'cd /source && tar -czf - .' > "$MEDIA_FILE"
[[ -s "$DB_FILE" && -s "$MEDIA_FILE" ]] || exit 1
chmod 600 "$DB_FILE" "$MEDIA_FILE"
(cd "$OUT" && sha256sum "$(basename "$DB_FILE")" "$(basename "$MEDIA_FILE")") > "$OUT/velmora-db-${STAMP}.sha256"
printf 'version=%s\ncreated_utc=%s\n' "$(cat VERSION)" "$STAMP" > "$OUT/velmora-backup-${STAMP}.txt"
echo "Local backup: $DB_FILE"
