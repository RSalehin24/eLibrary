#!/usr/bin/env bash

set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
source "$(cd -- "$(dirname -- "${SCRIPT_PATH}")/../.." >/dev/null 2>&1 && pwd)/automation/lib/common.sh"
REPO_ROOT="$(repo_root_from "${SCRIPT_PATH}")"

usage() {
  cat <<'EOF'
Usage:
  deploy/scripts/generate-env.sh <target>

Targets:
  production   -> deploy/env/.production.env
  test         -> deploy/env/.test.env
  host         -> deploy/env/.host.env
  all          -> generate production, test, and host files
EOF
}

generate_target() {
  local template_file="$1"
  local target_file="$2"
  ensure_env_file "${template_file}" "${target_file}"
  print_info "Prepared ${target_file}"
}

main() {
  local target_name="${1:-}"

  case "${target_name}" in
    production|test|host|all)
      ;;
    -h|--help|"")
      usage
      exit 0
      ;;
    *)
      usage
      die "Unsupported target: ${target_name}"
      ;;
  esac

  case "${target_name}" in
    production)
      generate_target "${REPO_ROOT}/deploy/env/app.env.example" "${REPO_ROOT}/deploy/env/.production.env"
      ;;
    test)
      generate_target "${REPO_ROOT}/deploy/env/app.env.example" "${REPO_ROOT}/deploy/env/.test.env"
      ;;
    host)
      generate_target "${REPO_ROOT}/deploy/env/host.env.example" "${REPO_ROOT}/deploy/env/.host.env"
      ;;
    all)
      generate_target "${REPO_ROOT}/deploy/env/app.env.example" "${REPO_ROOT}/deploy/env/.production.env"
      generate_target "${REPO_ROOT}/deploy/env/app.env.example" "${REPO_ROOT}/deploy/env/.test.env"
      generate_target "${REPO_ROOT}/deploy/env/host.env.example" "${REPO_ROOT}/deploy/env/.host.env"
      ;;
  esac
}

main "$@"
