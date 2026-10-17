#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/_local-compose.sh
source "$ROOT_DIR/scripts/_local-compose.sh"
velmora_local_prepare "$ROOT_DIR"
if [[ $# -gt 0 ]]; then
  velmora_local_compose logs --tail=200 -f "$@"
else
  velmora_local_compose logs --tail=200 -f
fi
