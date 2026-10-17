#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/_local-compose.sh
source "$ROOT_DIR/scripts/_local-compose.sh"
velmora_local_prepare "$ROOT_DIR"
velmora_local_compose down "$@"
