#!/usr/bin/env bash

set -euo pipefail

: "${SCRIPT_PATH:=${BASH_SOURCE[0]}}"
source "$(cd -- "$(dirname -- "${SCRIPT_PATH}")/../.." >/dev/null 2>&1 && pwd)/automation/lib/common.sh"
REPO_ROOT="$(repo_root_from "${SCRIPT_PATH}")"
export REPO_ROOT

HOST_ENV_TEMPLATE="${REPO_ROOT}/deploy/env/host.env.example"
HOST_ENV_FILE="${REPO_ROOT}/deploy/env/.host.env"
APP_ENV_TEMPLATE="${REPO_ROOT}/deploy/env/app.env.example"
REMOTE_APP_ENV_REL="deploy/env/.app.env"
DEPLOY_COMPOSE_REL="deploy/compose/docker-compose.yml"
REMOTE_SUPER_ADMIN_NOTICE_MARKER="deploy/env/.superadmin_credentials_noted"

usage() {
  cat <<'EOF'
Usage:
  deploy/scripts/deploy.sh [--env-name production|test] [--env-file /path/to/file] [--sync-mode push|preserve|prompt]

Options:
  --env-name    Environment name. Defaults to 'production'. Controls which .env file is loaded.
  --env-file    Explicit path to the app env file. Overrides --env-name.
  --sync-mode   How to handle the remote app env file:
                  push     - overwrite the remote env with the local file (default)
                  preserve - keep whatever is already on the server
                  prompt   - ask interactively at runtime

Before deploying:
  1. Fill in deploy/env/.host.env  (server username, IP, domain, certbot email)
  2. Fill in deploy/env/.production.env  (Django secret key, super admin credentials, DB URL)
  Run: deploy/scripts/generate-env.sh host
       deploy/scripts/generate-env.sh production

Examples:
  deploy/scripts/deploy.sh
  deploy/scripts/deploy.sh --env-name test --sync-mode preserve

On the first successful deployment to a remote app directory, the configured
super admin email and password are printed once so you can record them.
EOF
}

resolve_domain_ips() {
  python3 - "$1" <<'PY'
import socket
import sys

domain = sys.argv[1]
try:
    _name, _aliases, ips = socket.gethostbyname_ex(domain)
except Exception:
    ips = []

print("\n".join(sorted(set(ips))))
PY
}

extract_database_url_host() {
  python3 - "$1" <<'PY'
from urllib.parse import urlparse
import sys

parsed = urlparse((sys.argv[1] or "").strip())
print(parsed.hostname or "")
PY
}

extract_database_url_user() {
  python3 - "$1" <<'PY'
from urllib.parse import urlparse
import sys

parsed = urlparse((sys.argv[1] or "").strip())
print(parsed.username or "")
PY
}

require_non_empty_env_key() {
  local env_file="${1:?env file is required}"
  local key_name="${2:?env key is required}"
  local value
  value="$(grep "^${key_name}=" "${env_file}" | tail -n 1 | cut -d '=' -f2- || true)"
  [[ -n "${value}" ]] || die "Action required: ${key_name} must be set in ${env_file}"
}

validate_local_database_env() {
  local env_file="${1:?env file is required}"
  local database_url database_host database_user postgres_user

  [[ -f "${env_file}" ]] || die "Action required: missing env file ${env_file}"
  database_url="$(grep '^DATABASE_URL=' "${env_file}" | tail -n 1 | cut -d '=' -f2- || true)"
  [[ -n "${database_url}" ]] || die "Action required: DATABASE_URL is missing in ${env_file}"

  database_host="$(extract_database_url_host "${database_url}")"
  [[ "${database_host}" == "postgres" ]] || die "Action required: DATABASE_URL host must be postgres for docker networking. Found: ${database_host:-<empty>}"

  database_user="$(extract_database_url_user "${database_url}")"
  postgres_user="$(grep '^POSTGRES_USER=' "${env_file}" | tail -n 1 | cut -d '=' -f2- || true)"
  if [[ -n "${postgres_user}" && -n "${database_user}" && "${database_user}" != "${postgres_user}" ]]; then
    die "Action required: DATABASE_URL username (${database_user}) and POSTGRES_USER (${postgres_user}) must match in ${env_file}"
  fi
}

sync_remote_repository() {
  echo
  print_info "[2/8] Syncing repository on ${TARGET}"
  ssh -A "${TARGET}" \
    REPO_SSH="${REPO_SSH}" \
    BRANCH="${BRANCH}" \
    APP_DIR="${REMOTE_APP_DIR}" \
    DOMAIN="${DOMAIN}" \
    BACKEND_PORT="${BACKEND_PORT}" \
    FRONTEND_PORT="${FRONTEND_PORT}" \
    'bash -s' <<'EOF'
set -euo pipefail

set_default_env() {
  local key="$1"
  local value="$2"
  local file="$3"

  if grep -q "^${key}=" "${file}"; then
    local current_value
    current_value="$(grep "^${key}=" "${file}" | head -n 1 | cut -d '=' -f2-)"
    if [[ -z "${current_value}" ]]; then
      sed -i "s|^${key}=.*|${key}=${value}|" "${file}"
    fi
  else
    printf '\n%s=%s\n' "${key}" "${value}" >>"${file}"
  fi
}

mkdir -p "${APP_DIR}"
if [[ -d "${APP_DIR}/.git" ]]; then
  cd "${APP_DIR}"
  git fetch origin "${BRANCH}"
  if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
    git checkout "${BRANCH}"
  else
    git checkout -B "${BRANCH}" "origin/${BRANCH}"
  fi
  git reset --hard "origin/${BRANCH}"
else
  rm -rf "${APP_DIR}"
  git clone "${REPO_SSH}" "${APP_DIR}"
  cd "${APP_DIR}"
  git checkout -B "${BRANCH}" "origin/${BRANCH}"
fi

mkdir -p deploy/env logs/local logs/remote app/backend/storage/staticfiles app/backend/storage/media app/backend/storage/media/scraped-books
python3 automation/lib/env_tools.py scaffold deploy/env/app.env.example deploy/env/.app.env
set_default_env PUBLIC_BASE_URL "https://${DOMAIN}" deploy/env/.app.env
set_default_env PUBLIC_API_ORIGIN "https://${DOMAIN}" deploy/env/.app.env
set_default_env FRONTEND_BASE_URL "https://${DOMAIN}" deploy/env/.app.env
set_default_env VITE_API_BASE_URL "/api" deploy/env/.app.env
set_default_env BACKEND_PORT "${BACKEND_PORT}" deploy/env/.app.env
set_default_env FRONTEND_PORT "${FRONTEND_PORT}" deploy/env/.app.env
set_default_env RUNTIME_STORAGE_DIR "/app/storage" deploy/env/.app.env

printf 'Remote repository ready at %s\n' "${APP_DIR}"
EOF
}

sync_workspace_files() {
  echo
  print_info "[3/8] Syncing workspace content to ${TARGET}"
  (
    cd "${REPO_ROOT}"
    COPYFILE_DISABLE=1 COPY_EXTENDED_ATTRIBUTES_DISABLE=1 tar --no-mac-metadata -czf - \
      --exclude='.git' \
      --exclude='.DS_Store' \
      --exclude='venv' \
      --exclude='.venv' \
      --exclude='app/frontend/node_modules' \
      --exclude='app/frontend/dist' \
      --exclude='app/frontend/test-results' \
      --exclude='app/frontend/test-artifacts' \
      --exclude='app/backend/storage' \
      --exclude='app/backend/staticfiles' \
      --exclude='app/backend/celerybeat-schedule' \
      --exclude='app/backend/__pycache__' \
      --exclude='app/backend/apps/*/__pycache__' \
      --exclude='tests/backend/__pycache__' \
      --exclude='test-artifacts' \
      --exclude='local' \
      --exclude='migration/runtime' \
      --exclude='logs/local' \
      --exclude='logs/remote' \
      --exclude='deploy/env/.host.env' \
      --exclude='deploy/env/.production.env' \
      --exclude='deploy/env/.test.env' \
      --exclude='deploy/env/.app.env' \
      --exclude='*.pyc' \
      .
  ) | ssh "${TARGET}" "tar --warning=no-unknown-keyword --no-same-owner --no-same-permissions -xzf - -C '${REMOTE_APP_ABS_DIR}'"
}

sync_ebangla_auth_file() {
  # app/backend/storage is excluded from the workspace tar (it holds runtime
  # data), so the ebanglalibrary.com auth cookies must be copied explicitly.
  # Generated locally by: bash local/scripts/save-ebangla-auth.sh
  local auth_file="${REPO_ROOT}/app/backend/storage/ebangla_auth.json"
  local remote_dir="${REMOTE_APP_ABS_DIR}/app/backend/storage"

  if [[ ! -f "${auth_file}" ]]; then
    print_info "No ebangla_auth.json found locally; skipping auth-cookie sync (multi-page TOC scraping will be limited until you run local/scripts/save-ebangla-auth.sh)."
    return 0
  fi

  print_info "Syncing ebanglalibrary.com auth cookies to ${TARGET}"
  ssh "${TARGET}" "mkdir -p '${remote_dir}'"
  scp "${auth_file}" "${TARGET}:${remote_dir}/ebangla_auth.json" >/dev/null
  print_info "Auth cookies synced to ${remote_dir}/ebangla_auth.json"
}

sync_remote_env_file() {
  local sync_mode="${1:?sync mode is required}"
  echo
  echo
  print_info "[4/8] Syncing application env to ${TARGET}"
  if [[ "${sync_mode}" == "preserve" ]]; then
    print_info "Preserving remote ${REMOTE_APP_ENV_REL} values"
    return 0
  fi

  [[ -f "${LOCAL_ENV_FILE}" ]] || die "Action required: local env file not found: ${LOCAL_ENV_FILE}"

  scp "${LOCAL_ENV_FILE}" "${TARGET}:${REMOTE_APP_ABS_DIR}/deploy/env/.env.sync" >/dev/null
  ssh "${TARGET}" "cd '${REMOTE_APP_ABS_DIR}' && python3 automation/lib/env_tools.py merge ${REMOTE_APP_ENV_REL} deploy/env/.env.sync deploy/env/.app.env.merged --non-empty-only && mv deploy/env/.app.env.merged ${REMOTE_APP_ENV_REL} && rm -f deploy/env/.env.sync"
  print_info "[4/8] Merged non-empty values from $(basename "${LOCAL_ENV_FILE}") into ${REMOTE_APP_ENV_REL}"
}

refresh_ports_from_remote_env() {
  local remote_backend_port remote_frontend_port

  remote_backend_port="$(ssh "${TARGET}" "cd '${REMOTE_APP_ABS_DIR}' && awk -F '=' '/^BACKEND_PORT=/{print \$2}' '${REMOTE_APP_ENV_REL}' | tail -n 1" 2>/dev/null || true)"
  remote_frontend_port="$(ssh "${TARGET}" "cd '${REMOTE_APP_ABS_DIR}' && awk -F '=' '/^FRONTEND_PORT=/{print \$2}' '${REMOTE_APP_ENV_REL}' | tail -n 1" 2>/dev/null || true)"

  if [[ -n "${remote_backend_port}" && "${remote_backend_port}" =~ ^[0-9]+$ ]]; then
    BACKEND_PORT="${remote_backend_port}"
  fi

  if [[ -n "${remote_frontend_port}" && "${remote_frontend_port}" =~ ^[0-9]+$ ]]; then
    FRONTEND_PORT="${remote_frontend_port}"
  fi

  print_info "[4/8] Using runtime ports backend:${BACKEND_PORT} frontend:${FRONTEND_PORT}"
  echo
}

ensure_remote_docker() {
  local needs_install

  needs_install="$(
    ssh "${TARGET}" "if ! command -v docker >/dev/null 2>&1; then echo yes; elif ! docker compose version >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then echo yes; elif [ -n '${DEPLOY_DOCKER_VERSION}' ] && ! docker --version | grep -Fq '${DEPLOY_DOCKER_VERSION}'; then echo yes; else echo no; fi"
  )"
  echo
  if [[ "${needs_install}" == "yes" ]]; then
    print_info "[5/8] Installing or upgrading Docker on ${TARGET}"
    ssh -t "${TARGET}" "cd '${REMOTE_APP_ABS_DIR}' && sudo bash deploy/scripts/install-docker.sh '${DEPLOY_DOCKER_VERSION}'"
  else
    print_info "[5/8] Docker already satisfies deployment requirements"
  fi
}

start_remote_stack() {
  echo
  print_info "[6/8] Starting dockerized frontend and backend on ${TARGET}"
  ssh "${TARGET}" "cd '${REMOTE_APP_ABS_DIR}' && BACKEND_PORT='${BACKEND_PORT}' FRONTEND_PORT='${FRONTEND_PORT}' bash -s" <<'EOF'
set -euo pipefail

source automation/lib/common.sh

if docker compose version >/dev/null 2>&1; then
  compose_cmd=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose_cmd=(docker-compose)
else
  echo "Docker Compose is not available after Docker setup." >&2
  exit 1
fi

rm -f deploy/env/.app.compose.env
load_env_if_present deploy/env/.app.env

compose_args=(-f deploy/compose/docker-compose.yml)

"${compose_cmd[@]}" "${compose_args[@]}" down --remove-orphans || true
"${compose_cmd[@]}" "${compose_args[@]}" up -d --build --force-recreate

if ! "${compose_cmd[@]}" "${compose_args[@]}" exec -T worker python - <<'PY'
import socket

socket.getaddrinfo('ebanglalibrary.com', 443)
print('ok')
PY
then
  echo "Worker container could not resolve ebanglalibrary.com" >&2
  "${compose_cmd[@]}" "${compose_args[@]}" logs --tail=60 worker
  exit 1
fi

check_published_port() {
  local service="$1"
  local container_port="$2"
  local expected="127.0.0.1:$3"
  local published=""

  for _ in $(seq 1 20); do
    published="$("${compose_cmd[@]}" "${compose_args[@]}" port "${service}" "${container_port}" 2>/dev/null || true)"
    if [[ "${published}" == "${expected}" ]]; then
      return 0
    fi
    sleep 2
  done

  echo "Port binding mismatch for ${service}: expected ${expected}, got ${published:-<none>}" >&2
  "${compose_cmd[@]}" "${compose_args[@]}" ps
  return 1
}

check_published_port backend 8000 "${BACKEND_PORT}"
check_published_port frontend 80 "${FRONTEND_PORT}"

http_probe() {
  local url="$1"

  if command -v curl >/dev/null 2>&1; then
    local status
    status="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "${url}" 2>/dev/null || true)"
    [[ -n "${status}" && "${status}" != "000" && "${status:0:1}" != "5" ]]
    return
  fi

  if command -v wget >/dev/null 2>&1; then
    wget -q --spider --timeout=10 "${url}"
    return
  fi

  return 127
}

wait_for_http_ready() {
  local url="$1"
  local service_name="$2"
  local attempts=30
  local attempt

  for attempt in $(seq 1 "${attempts}"); do
    if http_probe "${url}"; then
      return 0
    fi
    sleep 2
  done

  echo "Timed out waiting for ${service_name} at ${url}" >&2
  return 1
}

if ! wait_for_http_ready "http://127.0.0.1:${BACKEND_PORT}/api/csrf/" "backend readiness"; then
  "${compose_cmd[@]}" "${compose_args[@]}" ps
  "${compose_cmd[@]}" "${compose_args[@]}" logs --tail=120 backend backend-init
  exit 1
fi

if ! wait_for_http_ready "http://127.0.0.1:${FRONTEND_PORT}/" "frontend readiness"; then
  "${compose_cmd[@]}" "${compose_args[@]}" ps
  "${compose_cmd[@]}" "${compose_args[@]}" logs --tail=120 frontend
  exit 1
fi
EOF
}

