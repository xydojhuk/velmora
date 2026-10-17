#!/usr/bin/env bash
# Shared helpers for Velmora local Docker Compose commands.

velmora_local_prepare() {
  local root_dir="$1"
  cd "$root_dir"

  [[ -f .env.local ]] || cp .env.local.example .env.local
  ./scripts/local-init.sh >/dev/null

  local pg setup installed
  pg="$(awk -F= '$1=="VELMORA_LOCAL_PG_BOOTSTRAP_PASSWORD" {sub(/^[^=]*=/,""); print; exit}' .env.local)"
  setup="$(awk -F= '$1=="VELMORA_LOCAL_SETUP_TOKEN" {sub(/^[^=]*=/,""); print; exit}' .env.local)"
  installed=0
  [[ -f .bootstrap/installed.lock ]] && installed=1

  if [[ -z "$pg" ]]; then
    echo "Local bootstrap error: PostgreSQL bootstrap password is missing from .env.local." >&2
    return 1
  fi
  if [[ "$installed" -eq 0 && -z "$setup" ]]; then
    echo "Local bootstrap error: setup token is missing from .env.local." >&2
    return 1
  fi
}

velmora_local_compose() {
  VELMORA_BOOTSTRAP_DIR=./.bootstrap \
  VELMORA_BOOTSTRAP_PG_SECRET_FILE=./.bootstrap/postgres_bootstrap_password \
  VELMORA_BOOTSTRAP_MODE=local \
  VELMORA_SITE_URL=http://velmora.local \
  docker compose --env-file .env.local -f compose.yaml -f compose.local.yaml "$@"
}
