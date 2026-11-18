#!/usr/bin/env bash

set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
source "$(cd -- "$(dirname -- "${SCRIPT_PATH}")/../.." >/dev/null 2>&1 && pwd)/automation/lib/common.sh"
REPO_ROOT="$(repo_root_from "${SCRIPT_PATH}")"

usage() {
  cat <<'EOF'
Usage:
  tests/scripts/test-frontend-unit.sh [node test args...]
  tests/scripts/test-frontend-unit.sh -- [node test args starting with -]

Examples:
  tests/scripts/test-frontend-unit.sh
  tests/scripts/test-frontend-unit.sh -- --test-name-pattern access

Runs the frontend unit test suite from app/frontend.
No Docker services are started because these tests run locally.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" == "--" ]]; then
  shift
fi

print_info "Running frontend unit tests"
(
  cd "${REPO_ROOT}/app/frontend"
  npm run test:unit -- "$@"
)
