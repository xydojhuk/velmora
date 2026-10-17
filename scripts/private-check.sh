#!/usr/bin/env bash
# Offline code/preflight checks; no Git and no Docker required.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
python3 scripts/check-version.py
python3 scripts/check-private-config.py
python3 scripts/sync-storefront-defaults.py --check
node scripts/test-storefront-copy.mjs
python3 scripts/test-backup-validator.py
python3 scripts/test-release-policy.py
for file in scripts/*.sh velmora.sh; do bash -n "$file"; done
find backend/app backend/alembic backend/tests -name '*.py' -type f -print0 | xargs -0 -r python3 -m py_compile
find frontend/src frontend/scripts -name '*.js' -o -name '*.mjs' | while IFS= read -r file; do node --check "$file"; done
echo 'All offline checks passed. npm build, PostgreSQL and Docker E2E are separate.'
