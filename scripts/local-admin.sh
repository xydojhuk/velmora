#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/_local-compose.sh
source "$ROOT_DIR/scripts/_local-compose.sh"
velmora_local_prepare "$ROOT_DIR"
read -r -p "Administrator email [admin@velmora.local]: " ADMIN_EMAIL
ADMIN_EMAIL=${ADMIN_EMAIL:-admin@velmora.local}
read -r -p "Administrator name [Administrator]: " ADMIN_NAME
ADMIN_NAME=${ADMIN_NAME:-Administrator}
velmora_local_compose exec backend python -m app.cli create-admin --email "$ADMIN_EMAIL" --name "$ADMIN_NAME"
