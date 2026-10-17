#!/usr/bin/env bash
set -euo pipefail
[[ "${EUID:-$(id -u)}" -eq 0 ]] || exec sudo bash "$0" "$@"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=/etc/velmora/velmora.env
[[ -f "$ENV_FILE" ]] || { echo "Production server bootstrap not found" >&2; exit 1; }
usage() { echo "Usage: sudo ./velmora.sh restore PATH_TO_DB.dump [--apply --confirm RESTORE]"; exit 2; }
[[ $# -ge 1 ]] || usage
DB_FILE="$(realpath -e "$1")"
[[ "$DB_FILE" == *.dump ]] || usage
MEDIA_FILE="${DB_FILE%.dump}"; MEDIA_FILE="${MEDIA_FILE/velmora-db-/velmora-media-}.tar.gz"
[[ -s "$DB_FILE" && -s "$MEDIA_FILE" ]] || { echo "Missing database dump or paired media archive" >&2; exit 1; }
CHECK_FILE="${DB_FILE%.dump}.sha256"
python3 "$ROOT_DIR/scripts/validate-backup.py" "$DB_FILE"

docker run --rm --network none -v "$(dirname "$DB_FILE"):/backup:ro,Z" postgres:18.6-alpine pg_restore --list "/backup/$(basename "$DB_FILE")" >/dev/null
docker run --rm --network none -v "$(dirname "$MEDIA_FILE"):/backup:ro,Z" alpine:3.22 tar -tzf "/backup/$(basename "$MEDIA_FILE")" >/dev/null
if [[ "${2:-}" != "--apply" || "${3:-}" != "--confirm" || "${4:-}" != "RESTORE" ]]; then
  echo "Dry-run OK. This archive can be opened. Nothing has been changed."
  echo "DANGER: --apply replaces the CURRENT database and media, not just missing rows."
  echo "Run: sudo ./velmora.sh restore '$DB_FILE' --apply --confirm RESTORE"
  exit 0
fi
cd "$ROOT_DIR"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.yaml")
# Extra recovery point BEFORE touching current state.
"$ROOT_DIR/scripts/backup.sh" --quiesce
RUNTIME_ENV="$(docker run --rm --network none -v velmora_runtime_config:/cfg:ro alpine:3.22 cat /cfg/runtime.env)"
val(){ printf '%s\n' "$RUNTIME_ENV" | sed -n "s/^$1=//p" | head -n1; }
DB_HOST="$(val DATABASE_HOST)"; DB_PORT="$(val DATABASE_PORT)"; DB_USER="$(val DATABASE_USER)"; DB_NAME="$(val DATABASE_NAME)"; DB_SSLMODE="$(val DATABASE_SSLMODE)"
DB_PASSWORD="$(docker run --rm --network none -v velmora_runtime_secrets:/sec:ro alpine:3.22 cat /sec/database_password)"
[[ -n "$DB_HOST" && -n "$DB_USER" && -n "$DB_NAME" && -n "$DB_PASSWORD" ]] || exit 1
NETWORK=velmora_edge; [[ "$DB_HOST" == postgres ]] && NETWORK=velmora_data
"${COMPOSE[@]}" stop frontend backend
# A failure intentionally leaves the application stopped; do not serve a partially restored DB.
trap 'echo "Restore interrupted. Application kept stopped; inspect logs before restart." >&2' ERR
cat "$DB_FILE" | docker run --rm -i --network "$NETWORK" -e PGPASSWORD="$DB_PASSWORD" -e PGSSLMODE="${DB_SSLMODE:-prefer}" postgres:18.6-alpine \
  pg_restore --exit-on-error --clean --if-exists --no-owner --no-privileges -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER" -d "$DB_NAME"
cat "$MEDIA_FILE" | docker run --rm -i --network none -v velmora_media_data:/target alpine:3.22 sh -ec \
  'rm -rf /target/* /target/.[!.]* /target/..?*; cd /target; tar -xzf -'
"${COMPOSE[@]}" up -d --no-build
trap - ERR
"${COMPOSE[@]}" ps
printf 'Restore completed. Run: sudo ./velmora.sh preflight\n'
