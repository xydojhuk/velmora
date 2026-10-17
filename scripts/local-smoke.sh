#!/usr/bin/env bash
# Non-destructive GET/health checks against a local Velmora installation.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
source scripts/_local-compose.sh
velmora_local_prepare "$ROOT_DIR"
velmora_local_compose config -q
velmora_local_compose ps

failures=0
check_code() {
  local path="$1" expected="$2" got
  got="$(curl -sS --connect-timeout 4 --max-time 12 --resolve velmora.local:80:127.0.0.1 -o /dev/null -w '%{http_code}' "http://velmora.local${path}" 2>/dev/null || :)"
  if [[ "$got" == "$expected" ]]; then echo "PASS GET ${path}: ${got}"
  else echo "FAIL GET ${path}: ${got} (expected ${expected})" >&2; failures=$((failures+1)); fi
}
check_code / 200
check_code /healthz 200
check_code /admin/products 200
check_code /admin/categories 200
check_code /api/v1/public/config 200
check_code /api/v1/public/products 200
check_code /api/v1/public/categories 200
check_code /robots.txt 200
check_code /sitemap.xml 200

# Ensure the runtime database schema has been migrated to this patch's head.
current="$(velmora_local_compose exec -T backend python -m alembic current 2>&1 || true)"
if [[ "$current" == *0010_categories_and_idempotency* ]]; then echo "PASS Alembic schema head: 0010"
else echo "FAIL Alembic head is not 0010: $current" >&2; failures=$((failures+1)); fi

if ((failures > 0)); then echo "$failures checks failed" >&2; exit 1; fi
echo 'Local read-only smoke tests passed. Continue with manual checkout and restore tests.'
