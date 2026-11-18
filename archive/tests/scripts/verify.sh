#!/usr/bin/env bash

set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
source "$(cd -- "$(dirname -- "${SCRIPT_PATH}")/../.." >/dev/null 2>&1 && pwd)/automation/lib/common.sh"
REPO_ROOT="$(repo_root_from "${SCRIPT_PATH}")"
export REPO_ROOT

repeat_count=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repeat)
      repeat_count="${2:?--repeat requires a count}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Usage:
  tests/scripts/verify.sh [--repeat N]

Runs the real Dockerized stack, seeds deterministic browser data, executes
backend tests inside the backend container, builds the frontend inside the
frontend container, and runs the live Playwright browser suite.
EOF
      exit 0
      ;;
    *)
      die "Unsupported argument: $1"
      ;;
  esac
done

require_cmd npm
require_cmd curl
require_cmd python3

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

run_backend_tests() {
  compose "${COMPOSE_ARGS[@]}" exec -T backend sh -lc \
    "cd /app && PYTHONPATH=/app DJANGO_SETTINGS_MODULE=config.settings pytest -c /workspace/tests/pytest.ini -o cache_dir=/tmp/pytest-cache /workspace/tests/backend -q"
}

run_frontend_unit_tests() {
  (
    cd "${REPO_ROOT}/app/frontend"
    npm run test:unit
  )
}

run_frontend_build() {
  compose "${COMPOSE_ARGS[@]}" exec -T frontend sh -lc \
    "cd /app && npm run build"
}

run_browser_suite() {
  local browser_test_args="${PLAYWRIGHT_VERIFY_ARGS:---workers=1}"

  (
    cd "${REPO_ROOT}/app/frontend"
    PLAYWRIGHT_BASE_URL="${FRONTEND_URL}" \
    PLAYWRIGHT_SKIP_STACK_START=1 \
    PLAYWRIGHT_SKIP_E2E_SEED=1 \
    npm run test:e2e -- ${browser_test_args}
  )
}

for run_index in $(seq 1 "${repeat_count}"); do
  print_info "Verification run ${run_index}/${repeat_count}: file-size policy"
  python3 "${REPO_ROOT}/tests/scripts/check-file-size-policy.py"

  print_info "Verification run ${run_index}/${repeat_count}: architecture policy"
  python3 "${REPO_ROOT}/tests/scripts/check-architecture-policy.py"

  print_info "Verification run ${run_index}/${repeat_count}: starting live stack"
  compose "${COMPOSE_ARGS[@]}" up -d --build "${STACK_SERVICES[@]}"
  compose "${COMPOSE_ARGS[@]}" stop worker processing-worker beat >/dev/null 2>&1 || true

  print_info "Verification run ${run_index}/${repeat_count}: waiting for services"
  wait_for_url "${FRONTEND_URL}" 120 || die "Frontend did not become ready at ${FRONTEND_URL}"
  wait_for_url "${BACKEND_SESSION_URL}" 120 || die "Backend did not become ready at ${BACKEND_SESSION_URL}"

  print_info "Verification run ${run_index}/${repeat_count}: seeding live browser data"
  "${REPO_ROOT}/tests/scripts/seed-e2e-data.sh"

  print_info "Verification run ${run_index}/${repeat_count}: reconfirming services after seed"
  wait_for_url "${FRONTEND_URL}" 120 || die "Frontend did not become ready at ${FRONTEND_URL} after seed"
  wait_for_url "${BACKEND_SESSION_URL}" 120 || die "Backend did not become ready at ${BACKEND_SESSION_URL} after seed"

  print_info "Verification run ${run_index}/${repeat_count}: backend tests"
  run_backend_tests

  print_info "Verification run ${run_index}/${repeat_count}: frontend unit tests"
  run_frontend_unit_tests

  print_info "Verification run ${run_index}/${repeat_count}: frontend build"
  run_frontend_build

  print_info "Verification run ${run_index}/${repeat_count}: live browser suite"
  run_browser_suite
done
