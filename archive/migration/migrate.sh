#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
_SCRIPT_DIR="$(cd -- "$(dirname -- "${SCRIPT_PATH}")" >/dev/null 2>&1 && pwd)"
_SCRIPT_STEPS=(
  "configuration_and_arguments.sh"
  "preflight_remote_checks.sh"
  "source_freeze_checks.sh"
  "source_snapshot_capture.sh"
  "target_restore_checks.sh"
  "edge_verify_and_entrypoint.sh"
)
for _script_step in "${_SCRIPT_STEPS[@]}"; do
  _script_path="${_SCRIPT_DIR}/migrate_steps/${_script_step}"
  # shellcheck source=/dev/null
  source "${_script_path}"
done
