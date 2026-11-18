#!/usr/bin/env bash

set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
source "$(cd -- "$(dirname -- "${SCRIPT_PATH}")/../.." >/dev/null 2>&1 && pwd)/automation/lib/common.sh"
REPO_ROOT="$(repo_root_from "${SCRIPT_PATH}")"
export REPO_ROOT

require_cmd curl
require_cmd npm

usage() {
  cat <<'EOF'
Usage:
  tests/scripts/test-e2e.sh [Playwright args...]
  tests/scripts/test-e2e.sh -- [Playwright args starting with -]

Examples:
  tests/scripts/test-e2e.sh
  tests/scripts/test-e2e.sh processing-pages.spec.js
  tests/scripts/test-e2e.sh -- --workers=1

Starts the local Docker stack if needed, reseeds deterministic browser data,
and runs the live Playwright suite against the local application.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" == "--" ]]; then
  shift
fi

APP_ENV_FILE="${REPO_ROOT}/local/env/.env"
COMPOSE_FILE="${REPO_ROOT}/local/compose/docker-compose.yml"
COMPOSE_ARGS=(-f "${COMPOSE_FILE}")
STACK_SERVICES=(postgres redis backend frontend)
ensure_env_file "${REPO_ROOT}/local/env/app.env.example" "${APP_ENV_FILE}"
load_env_if_present "${APP_ENV_FILE}"

FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT:-5173}"
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

print_info "Starting local stack for browser tests"
compose "${COMPOSE_ARGS[@]}" up -d --build "${STACK_SERVICES[@]}"
compose "${COMPOSE_ARGS[@]}" stop worker processing-worker beat >/dev/null 2>&1 || true

print_info "Waiting for frontend and backend"
wait_for_url "${FRONTEND_URL}" 120 || die "Frontend did not become ready at ${FRONTEND_URL}"
wait_for_url "${BACKEND_SESSION_URL}" 120 || die "Backend did not become ready at ${BACKEND_SESSION_URL}"

print_info "Seeding deterministic browser data"
"${REPO_ROOT}/tests/scripts/seed-e2e-data.sh"

print_info "Reconfirming frontend and backend after seed"
wait_for_url "${FRONTEND_URL}" 120 || die "Frontend did not become ready at ${FRONTEND_URL} after seed"
wait_for_url "${BACKEND_SESSION_URL}" 120 || die "Backend did not become ready at ${BACKEND_SESSION_URL} after seed"

print_info "Running Playwright browser suite"
(
  cd "${REPO_ROOT}/app/frontend"
  PLAYWRIGHT_BASE_URL="${FRONTEND_URL}" \
  PLAYWRIGHT_SKIP_STACK_START=1 \
  PLAYWRIGHT_SKIP_E2E_SEED=1 \
  npm run test:e2e -- "$@"
)
