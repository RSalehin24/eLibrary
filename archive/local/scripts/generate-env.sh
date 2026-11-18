#!/usr/bin/env bash

set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
source "$(cd -- "$(dirname -- "${SCRIPT_PATH}")/../.." >/dev/null 2>&1 && pwd)/automation/lib/common.sh"
REPO_ROOT="$(repo_root_from "${SCRIPT_PATH}")"
export REPO_ROOT

usage() {
  cat <<'EOF'
Usage:
  local/scripts/generate-env.sh

Generate:
  local/env/.env
EOF
}

generate_local_env() {
  ensure_env_file "${REPO_ROOT}/local/env/app.env.example" "${REPO_ROOT}/local/env/.env"
  print_info "Prepared ${REPO_ROOT}/local/env/.env"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -gt 0 ]]; then
  usage
  die "local/scripts/generate-env.sh does not accept targets."
fi

generate_local_env
