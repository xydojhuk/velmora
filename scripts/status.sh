#!/usr/bin/env bash
set -euo pipefail
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then exec sudo bash "$0" "$@"; fi
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=/etc/velmora/velmora.env
[[ -f "$ENV_FILE" ]] || { echo "Velmora server bootstrap has not been started. Run: sudo ./scripts/install.sh"; exit 1; }
cd "$ROOT_DIR"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.yaml")
"${COMPOSE[@]}" ps -a

echo
INSTALLED="$("${COMPOSE[@]}" exec -T installer python -c "import json,urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/v1/install/status'))['installed'])" 2>/dev/null || echo False)"
if [[ "$INSTALLED" != "True" ]]; then
  echo "Browser installation is not complete yet."
  set -a; source "$ENV_FILE"; set +a
  echo "Installer: ${VELMORA_SITE_URL}/install"
  exit 0
fi

echo "Backend:"
"${COMPOSE[@]}" exec -T backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3).read().decode())"
echo
echo "Frontend:"
"${COMPOSE[@]}" exec -T frontend node -e "fetch('http://127.0.0.1:5173/healthz').then(async r=>console.log(await r.text())).catch(e=>{console.error(e);process.exit(1)})"
