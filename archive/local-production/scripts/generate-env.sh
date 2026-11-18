#!/usr/bin/env bash

set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
source "$(cd -- "$(dirname -- "${SCRIPT_PATH}")/../.." >/dev/null 2>&1 && pwd)/automation/lib/common.sh"
REPO_ROOT="$(repo_root_from "${SCRIPT_PATH}")"

usage() {
  cat <<'EOF'
Usage:
  local-production/scripts/generate-env.sh <target>

Targets:
  app          -> local-production/env/app.env
  config       -> local-production/env/local_prod_config.env
  all          -> generate both files
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
    app|config|all)
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
    app)
      generate_target "${REPO_ROOT}/local-production/env/app.env.example" "${REPO_ROOT}/local-production/env/app.env"
      ;;
    config)
      generate_target "${REPO_ROOT}/local-production/env/local_prod_config.env.example" "${REPO_ROOT}/local-production/env/local_prod_config.env"
      ;;
    all)
      generate_target "${REPO_ROOT}/local-production/env/app.env.example" "${REPO_ROOT}/local-production/env/app.env"
      generate_target "${REPO_ROOT}/local-production/env/local_prod_config.env.example" "${REPO_ROOT}/local-production/env/local_prod_config.env"
      ;;
  esac
}

main "$@"
