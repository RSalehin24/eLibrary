#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

bash "${SCRIPT_DIR}/local/scripts/ensure-dockerctl.sh" &&
dockerctl start &&
bash "${SCRIPT_DIR}/local/scripts/dev.sh" up
