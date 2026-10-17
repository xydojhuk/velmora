#!/usr/bin/env bash
# Release gate: fail closed when dependencies/checks are unavailable.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

command -v git >/dev/null || { echo 'Missing git' >&2; exit 1; }
git rev-parse --is-inside-work-tree | grep -qx true || { echo 'This must run from a Git repository' >&2; exit 1; }
[[ -z "$(git status --porcelain --untracked-files=normal)" ]] || { echo 'Commit all intended changes first; Git tree is dirty.' >&2; exit 1; }

python3 scripts/verify-release-tree.py --tracked
python3 scripts/sync-storefront-defaults.py --check

command -v gitleaks >/dev/null || { echo 'Install gitleaks v8 before releasing.' >&2; exit 1; }
gitleaks git --redact --exit-code 1 .

python3 -m compileall -q backend/app backend/alembic backend/installer_app.py
(
  cd backend
  python3 -m pytest -q
)
for script in scripts/*.sh velmora.sh; do bash -n "$script"; done

command -v npm >/dev/null || { echo 'Install Node.js/npm.' >&2; exit 1; }
(
  cd frontend
  npm ci --no-audit --no-fund
  npm run check
  npm run build
  npm audit --omit=dev --audit-level=high
)

command -v docker >/dev/null || { echo 'Docker/Compose required for release gate.' >&2; exit 1; }
docker compose version >/dev/null
# No local secrets embedded in prod config; use safe placeholder interpolation.
DOMAIN=example.com ACME_EMAIL=admin@example.com VELMORA_SITE_URL=https://example.com \
  VELMORA_BOOTSTRAP_DIR=./.bootstrap VELMORA_BOOTSTRAP_PG_SECRET_FILE=./.bootstrap/postgres_bootstrap_password \
  docker compose -f compose.yaml config --quiet

echo 'Release checks passed. Full browser E2E, fresh VPS, restore and security gate still require operator sign-off.'
