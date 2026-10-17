#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/_local-compose.sh"
velmora_local_prepare "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "Docker Engine and Docker Compose v2 are required."
  exit 1
fi

if ! velmora_local_compose up -d --build; then
  velmora_local_compose ps -a || true
  velmora_local_compose logs --tail=200 postgres installer frontend caddy backend || true
  exit 1
fi

status_json="$(velmora_local_compose exec -T installer python - <<'PY' 2>/dev/null || true
import urllib.request
try:
    print(urllib.request.urlopen('http://127.0.0.1:8080/api/v1/install/status', timeout=3).read().decode())
except Exception:
    print('')
PY
)"

installed="$(python - "$status_json" <<'PY' 2>/dev/null || echo unknown
import json, sys
try:
    data=json.loads(sys.argv[1])
    print('yes' if data.get('installed') else 'no')
except Exception:
    print('unknown')
PY
)"

if [[ "$installed" != "yes" ]]; then
  if ! python - "$status_json" <<'PY'
import json, sys
try:
    data=json.loads(sys.argv[1])
except Exception:
    print('Installer status endpoint did not return valid JSON.', file=sys.stderr)
    raise SystemExit(1)
checks={c.get('key'): c for c in data.get('checks', [])}
bad=[]
for key in ('Setup code', 'Bundled PostgreSQL'):
    item=checks.get(key)
    if not item or not item.get('ok'):
        bad.append(item or {'key': key, 'message': 'missing check'})
for item in bad:
    print(f"{item.get('key')}: {item.get('message', 'failed')}", file=sys.stderr)
raise SystemExit(1 if bad else 0)
PY
  then
    echo >&2
    echo "Velmora local bootstrap failed its in-container readiness check." >&2
    echo "This build uses .env.local for local bootstrap secrets and does not rely on host bind permissions." >&2
    echo "Run: ./scripts/local-repair-bootstrap.sh" >&2
    velmora_local_compose logs --tail=120 postgres installer >&2 || true
    exit 1
  fi
fi

velmora_local_compose ps -a
echo
setup_token="$(awk -F= '$1=="VELMORA_LOCAL_SETUP_TOKEN" {sub(/^[^=]*=/,""); print; exit}' .env.local)"
if [[ -n "$setup_token" && "$installed" != "yes" ]]; then
  echo "Browser installer: http://velmora.local/install"
  echo "One-time setup code: $setup_token"
else
  echo "Velmora is already installed or the setup code has been consumed."
  echo "Storefront: http://velmora.local"
fi
echo "Status: ./scripts/local-ps.sh"
echo "Logs:   ./scripts/local-logs.sh"
