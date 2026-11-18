#!/usr/bin/env bash

set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
source "$(cd -- "$(dirname -- "${SCRIPT_PATH}")/../.." >/dev/null 2>&1 && pwd)/automation/lib/common.sh"
REPO_ROOT="$(repo_root_from "${SCRIPT_PATH}")"
export REPO_ROOT

require_cmd curl

usage() {
  cat <<'EOF'
Usage:
  tests/scripts/seed-e2e-data.sh

Starts the local backend stack if needed, waits for the backend, and reseeds
deterministic live E2E data inside the backend container.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -gt 0 ]]; then
  usage
  die "This script does not accept arguments."
fi

APP_ENV_FILE="${REPO_ROOT}/local/env/.env"
COMPOSE_FILE="${REPO_ROOT}/local/compose/docker-compose.yml"
COMPOSE_ARGS=(-f "${COMPOSE_FILE}")
STACK_SERVICES=(postgres redis backend)
BACKEND_SESSION_URL=""

ensure_env_file "${REPO_ROOT}/local/env/app.env.example" "${APP_ENV_FILE}"
load_env_if_present "${APP_ENV_FILE}"

BACKEND_SESSION_URL="http://127.0.0.1:${BACKEND_PORT:-8000}/api/auth/session/"

wait_for_url() {
  local url="${1:?url is required}"
  local timeout_seconds="${2:-60}"
  local started_at
  started_at="$(date +%s)"

  while true; do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      return 0
    fi

    if (( $(date +%s) - started_at >= timeout_seconds )); then
      return 1
    fi

    sleep 1
  done
}

print_info "Starting local stack for deterministic E2E seed data"
compose "${COMPOSE_ARGS[@]}" up -d --build "${STACK_SERVICES[@]}"

print_info "Waiting for backend"
wait_for_url "${BACKEND_SESSION_URL}" 120 || die "Backend did not become ready at ${BACKEND_SESSION_URL}"

print_info "Seeding deterministic live E2E data inside the local backend container."
compose "${COMPOSE_ARGS[@]}" exec -T backend python manage.py seed_e2e_data
