#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
_SCRIPT_DIR="$(cd -- "$(dirname -- "${SCRIPT_PATH}")" >/dev/null 2>&1 && pwd)"
_SCRIPT_STEPS=(
  "environment_and_domain_checks.sh"
  "remote_deploy_flow.sh"
)
for _script_step in "${_SCRIPT_STEPS[@]}"; do
  _script_path="${_SCRIPT_DIR}/deploy_steps/${_script_step}"
  # shellcheck source=/dev/null
  source "${_script_path}"
done
