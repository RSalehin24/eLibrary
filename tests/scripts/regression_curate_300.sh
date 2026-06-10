#!/usr/bin/env bash
#
# Run the 300-book source site regression harness inside the running
# backend container. Resumable: rerun any number of times — URLs whose audit
# already succeeded are skipped automatically.
#
# Usage:
#   tests/scripts/regression_curate_300.sh                  # default 300 URLs
#   tests/scripts/regression_curate_300.sh --limit 50       # smoke run
#   tests/scripts/regression_curate_300.sh --retry-failed   # re-attempt failed URLs
#   tests/scripts/regression_curate_300.sh --purge-exports  # delete EPUB folders after each pass
#
# State JSON lives inside the container at
# /app/storage/regression-300/state.json and survives restarts via the
# backend volume. Pass --state /workspace/<path> to override.

set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
REPO_ROOT="$(cd -- "$(dirname -- "${SCRIPT_PATH}")/../.." >/dev/null 2>&1 && pwd)"

CONTAINER="${REGRESSION_BACKEND_CONTAINER:-compose-backend-1}"

if ! docker exec "${CONTAINER}" true >/dev/null 2>&1; then
    echo "regression-300: backend container ${CONTAINER} is not running." >&2
    echo "  start it with: cd local/compose && docker compose up -d backend" >&2
    exit 2
fi

docker exec "${CONTAINER}" sh -lc '
    mkdir -p /app/storage/regression-300/exports
    cd /app
    PYTHONPATH=/app DJANGO_SETTINGS_MODULE=config.settings \
        python scripts/regression_curate_300.py '"$*"'
'
