#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:-}" == version ]]; then
  cat "$ROOT_DIR/VERSION"
  exit 0
fi
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  exec sudo bash "$0" "$@"
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE=/etc/velmora/velmora.env

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Velmora server bootstrap has not been started yet."
  echo "Run: sudo ./scripts/install.sh"
  exit 1
fi

COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.yaml")

CMD=${1:-help}

case "$CMD" in
  status)
    "$ROOT_DIR/scripts/status.sh"
    ;;

  logs)
    if [[ -n "${2:-}" ]]; then
      "${COMPOSE[@]}" logs -f --tail=200 "$2"
    else
      "${COMPOSE[@]}" logs -f --tail=200
    fi
    ;;

  start)
    "${COMPOSE[@]}" up -d
    ;;

  stop)
    "${COMPOSE[@]}" stop
    ;;

  restart)
    "${COMPOSE[@]}" up -d --force-recreate
    ;;

  update)
    "$ROOT_DIR/scripts/update.sh"
    ;;

  backup)
    shift
    "$ROOT_DIR/scripts/backup.sh" "$@"
    ;;

  restore)
    shift
    "$ROOT_DIR/scripts/restore.sh" "$@"
    ;;

  rollback)
    shift
    "$ROOT_DIR/scripts/rollback.sh" "$@"
    ;;

  preflight)
    "$ROOT_DIR/scripts/preflight.sh"
    ;;

  audit)
    "$ROOT_DIR/scripts/dependency-audit.sh"
    ;;

  create-admin)
    "$ROOT_DIR/scripts/create-admin.sh"
    ;;

  configure-store)
    "$ROOT_DIR/scripts/configure-store.sh"
    ;;

  smtp-password)
    "$ROOT_DIR/scripts/set-smtp-password.sh"
    ;;

  telegram-token)
    "$ROOT_DIR/scripts/set-telegram-token.sh"
    ;;

  help|*)
    echo "VELMORA"
    echo
    echo "sudo ./velmora.sh status"
    echo "sudo ./velmora.sh logs [installer|backend|frontend|postgres|caddy]"
    echo "sudo ./velmora.sh start"
    echo "sudo ./velmora.sh stop"
    echo "sudo ./velmora.sh restart"
    echo "sudo ./velmora.sh update"
    echo "./velmora.sh version"
    echo "sudo ./velmora.sh backup"
    echo "sudo ./velmora.sh restore /var/backups/velmora/velmora-db-TIMESTAMP.dump [--apply --confirm RESTORE]"
    echo "sudo ./velmora.sh rollback [--apply --confirm ROLLBACK]"
    echo "sudo ./velmora.sh preflight"
    echo "sudo ./velmora.sh audit"
    echo "sudo ./velmora.sh create-admin"
    echo "sudo ./velmora.sh configure-store"
    echo "sudo ./velmora.sh smtp-password"
    echo "sudo ./velmora.sh telegram-token"
    ;;
esac