#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/_local-compose.sh"
cd "$ROOT_DIR"

./scripts/local-init.sh

echo
echo "Recreating local PostgreSQL and installer without host-secret permission dependency..."
velmora_local_compose up -d --force-recreate postgres installer

echo
echo "Installer status:"
velmora_local_compose exec -T installer python - <<'PY'
import json, urllib.request
u='http://127.0.0.1:8080/api/v1/install/status'
data=json.load(urllib.request.urlopen(u, timeout=5))
for c in data.get('checks', []):
    if c.get('key') in {'Setup code','Bundled PostgreSQL','Runtime configuration','Secret storage','Site URL'}:
        print(('OK  ' if c.get('ok') else 'FAIL') + ' ' + c.get('key','') + ': ' + str(c.get('message','')))
PY

echo
setup="$(awk -F= '$1=="VELMORA_LOCAL_SETUP_TOKEN" {sub(/^[^=]*=/,""); print; exit}' .env.local)"
echo "Bootstrap repaired successfully."
echo "Setup code: $setup"
echo "Open: http://velmora.local/install"
