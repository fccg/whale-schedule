#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

COMPOSE_CMD=(docker compose)

usage() {
  cat <<'EOF'
Usage:
  ./scripts/appctl.sh update [--no-cache]
  ./scripts/appctl.sh restart
  ./scripts/appctl.sh build [--no-cache]
  ./scripts/appctl.sh up
  ./scripts/appctl.sh down
  ./scripts/appctl.sh logs [backend|frontend]
  ./scripts/appctl.sh status

Commands:
  update      git pull + rebuild + restart services
  restart     restart services with current local code
  build       rebuild images only
  up          start services in background
  down        stop services
  logs        show compose logs, default is all services
  status      show service status

Options:
  --no-cache  build images without Docker cache
EOF
}

build_images() {
  local no_cache="${1:-false}"
  if [[ "${no_cache}" == "true" ]]; then
    "${COMPOSE_CMD[@]}" build --no-cache
  else
    "${COMPOSE_CMD[@]}" build
  fi
}

restart_stack() {
  local no_cache="${1:-false}"
  "${COMPOSE_CMD[@]}" down --remove-orphans
  build_images "${no_cache}"
  "${COMPOSE_CMD[@]}" up -d
  "${COMPOSE_CMD[@]}" ps
}

command="${1:-}"
shift || true

case "${command}" in
  update)
    no_cache="false"
    if [[ "${1:-}" == "--no-cache" ]]; then
      no_cache="true"
    fi
    git pull --ff-only
    restart_stack "${no_cache}"
    ;;
  restart)
    restart_stack "false"
    ;;
  build)
    no_cache="false"
    if [[ "${1:-}" == "--no-cache" ]]; then
      no_cache="true"
    fi
    build_images "${no_cache}"
    ;;
  up)
    "${COMPOSE_CMD[@]}" up -d
    "${COMPOSE_CMD[@]}" ps
    ;;
  down)
    "${COMPOSE_CMD[@]}" down --remove-orphans
    ;;
  logs)
    service="${1:-}"
    if [[ -n "${service}" ]]; then
      "${COMPOSE_CMD[@]}" logs -f "${service}"
    else
      "${COMPOSE_CMD[@]}" logs -f
    fi
    ;;
  status)
    "${COMPOSE_CMD[@]}" ps
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    echo "Unknown command: ${command}" >&2
    echo >&2
    usage
    exit 1
    ;;
esac
