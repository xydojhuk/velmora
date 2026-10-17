#!/usr/bin/env bash
set -euo pipefail
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then exec sudo bash "$0" "$@"; fi
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=/etc/velmora/velmora.env
BOOTSTRAP_DIR=/etc/velmora/bootstrap
[[ -f "$ENV_FILE" ]] || { echo "Run sudo ./scripts/install.sh first."; exit 1; }
cd "$ROOT_DIR"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.yaml")
INSTALLED="$("${COMPOSE[@]}" exec -T installer python -c "import json,urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/v1/install/status'))['installed'])" 2>/dev/null || echo unknown)"
if [[ "$INSTALLED" == "True" ]]; then echo "Velmora is already installed. The browser installer cannot be reopened."; exit 1; fi
umask 077
openssl rand -hex 12 > "$BOOTSTRAP_DIR/setup_token" 2>/dev/null || { od -An -N 12 -tx1 /dev/urandom | tr -d ' \n' > "$BOOTSTRAP_DIR/setup_token"; echo >> "$BOOTSTRAP_DIR/setup_token"; }
chmod 600 "$BOOTSTRAP_DIR/setup_token"
echo "New one-time setup code: $(cat "$BOOTSTRAP_DIR/setup_token")"
echo "Restart installer container so the bind mount sees the file if required:"
echo "docker compose --env-file '$ENV_FILE' -f '$ROOT_DIR/compose.yaml' restart installer"
