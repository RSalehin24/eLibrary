#!/usr/bin/env bash
# One-time helper to capture an example.com login session for the scraper.
#
# Cloudflare blocks every automated login, so we DON'T automate the login at all.
# Instead, log in to https://www.example.com once in Firefox
# (tick "Remember Me" so the cookie lasts ~1 year), then run this script. It
# reads the wordpress_logged_in_* cookie straight out of Firefox's cookie store
# and writes it to app/backend/storage/source_site_auth.json, which the backend reads
# automatically (locally via the storage bind-mount, on EC2 via the deploy sync).
#
# If the cookie can't be read automatically from Firefox, the script falls back
# to a manual paste prompt.
#
# Usage:
#   bash local/scripts/save-source-site-auth.sh
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." >/dev/null 2>&1 && pwd)"

cd "${REPO_ROOT}"

# Pick a Python interpreter: prefer the repo virtualenv if present.
if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PY="${REPO_ROOT}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  PY="python"
fi

echo "Using Python: ${PY}"

# Ensure browser-cookie3 is available for automatic cookie reads (idempotent).
# Not fatal if it can't install — the script still supports manual paste.
if ! "${PY}" -c "import browser_cookie3" >/dev/null 2>&1; then
  echo "Installing browser-cookie3 ..."
  "${PY}" -m pip install --quiet browser-cookie3 || \
    echo "(could not install browser-cookie3; manual paste mode will be used)"
fi

exec "${PY}" "${SCRIPT_DIR}/save_source_site_auth.py"
