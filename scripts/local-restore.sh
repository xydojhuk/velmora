#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# -ge 1 ]] || { echo "Usage: ./scripts/local-restore.sh .local/backups/velmora-db-TIMESTAMP.dump [--apply --confirm RESTORE]"; exit 2; }
DB_FILE="$(realpath -e "$1")"
MEDIA_FILE="${DB_FILE/velmora-db-/velmora-media-}"; MEDIA_FILE="${MEDIA_FILE%.dump}.tar.gz"
[[ -s "$DB_FILE" && -s "$MEDIA_FILE" ]] || { echo 'Incomplete backup' >&2; exit 1; }
CHECK="${DB_FILE%.dump}.sha256"
python3 "$ROOT_DIR/scripts/validate-backup.py" "$DB_FILE"
cd "$ROOT_DIR"
source "$ROOT_DIR/scripts/_local-compose.sh"
velmora_local_prepare "$ROOT_DIR"
docker run --rm -v "$(dirname "$DB_FILE"):/backup:ro,Z" --network none postgres:18.6-alpine pg_restore --list "/backup/$(basename "$DB_FILE")" >/dev/null
docker run --rm -v "$(dirname "$MEDIA_FILE"):/backup:ro,Z" --network none alpine:3.22 tar -tzf "/backup/$(basename "$MEDIA_FILE")" >/dev/null
if [[ "${2:-}" != '--apply' || "${3:-}" != '--confirm' || "${4:-}" != RESTORE ]]; then
 echo 'Dry-run OK; nothing changed. Use --apply --confirm RESTORE to OVERWRITE current local DB and media.'
 exit 0
fi
"$ROOT_DIR/scripts/local-backup.sh" --quiesce
RUNTIME_ENV="$(docker run --rm --network none -v velmora_runtime_config:/cfg:ro alpine:3.22 cat /cfg/runtime.env)"
val(){ printf '%s\n' "$RUNTIME_ENV" | sed -n "s/^$1=//p" | head -n1; }
DB_HOST="$(val DATABASE_HOST)"; DB_PORT="$(val DATABASE_PORT)"; DB_USER="$(val DATABASE_USER)"; DB_NAME="$(val DATABASE_NAME)"; DB_SSLMODE="$(val DATABASE_SSLMODE)"
DB_PASSWORD="$(docker run --rm --network none -v velmora_runtime_secrets:/sec:ro alpine:3.22 cat /sec/database_password)"
NETWORK=velmora_edge; [[ "$DB_HOST" == postgres ]] && NETWORK=velmora_data
velmora_local_compose stop frontend backend
trap 'echo "Restore failed; app remains stopped for investigation" >&2' ERR
cat "$DB_FILE" | docker run --rm -i --network "$NETWORK" -e PGPASSWORD="$DB_PASSWORD" -e PGSSLMODE="${DB_SSLMODE:-prefer}" postgres:18.6-alpine \
  pg_restore --exit-on-error --clean --if-exists --no-owner --no-privileges -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USER" -d "$DB_NAME"
cat "$MEDIA_FILE" | docker run --rm -i --network none -v velmora_media_data:/target alpine:3.22 sh -ec \
 'rm -rf /target/* /target/.[!.]* /target/..?*; cd /target; tar -xzf -'
velmora_local_compose up -d --no-build
trap - ERR
velmora_local_compose ps
