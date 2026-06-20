#!/usr/bin/env bash

set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${SCRIPT_PATH}")" >/dev/null 2>&1 && pwd)"
source "${SCRIPT_DIR}/../automation/lib/common.sh"
REPO_ROOT="$(repo_root_from "${SCRIPT_PATH}")"

LOCAL_PROD_DIR="${REPO_ROOT}/local-production"
APP_ENV_FILE="${LOCAL_PROD_DIR}/env/app.env"
CONFIG_ENV_FILE="${LOCAL_PROD_DIR}/env/local_prod_config.env"
COMPOSE_FILE="${LOCAL_PROD_DIR}/compose/docker-compose.yml"
CAFFEINATE_PID_FILE="${LOCAL_PROD_DIR}/.caffeinate.pid"
DEFAULT_SERVICES=(postgres redis backend worker processing-worker beat engine frontend)

usage() {
  cat <<'EOF'
Usage:
  local-production/deploy.sh [up|down|restart|logs|ps] [options]

Commands:
  up                    Build and start the local production stack (default)
  down                  Stop and remove all containers
  restart [service...]  Restart services
  logs [service...]     View logs
  ps                    List containers

Options:
  --branch <name>  Git branch to deploy (default: main)
  --no-pull        Skip git pull
  --no-sleep       Prevent macOS sleep & keep WiFi alive while stack is up
  -h, --help       Show this help

Examples:
  local-production/deploy.sh
  local-production/deploy.sh up --branch dev
  local-production/deploy.sh up --no-sleep
  local-production/deploy.sh down
  local-production/deploy.sh logs backend
  local-production/deploy.sh restart frontend
EOF
}

start_caffeinate() {
  if ! command -v caffeinate &>/dev/null; then
    print_warn "caffeinate not found on this system"
    return
  fi
  if [[ -f "${CAFFEINATE_PID_FILE}" ]]; then
    local pid
    pid="$(cat "${CAFFEINATE_PID_FILE}")"
    if kill -0 "${pid}" 2>/dev/null; then
      print_info "Wake lock already active (PID ${pid})"
      return
    fi
    rm -f "${CAFFEINATE_PID_FILE}"
  fi
  caffeinate -dimsu &
  local pid=$!
  echo "${pid}" > "${CAFFEINATE_PID_FILE}"
  print_info "Wake lock enabled — system will not sleep (PID ${pid})"
}

stop_caffeinate() {
  if [[ -f "${CAFFEINATE_PID_FILE}" ]]; then
    local pid
    pid="$(cat "${CAFFEINATE_PID_FILE}")"
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
      print_info "Wake lock disabled"
    fi
    rm -f "${CAFFEINATE_PID_FILE}"
  fi
}

print_banner() {
  local branch="${1:-main}"
  local frontend_port="${2:-8001}"
  local backend_port="${3:-8002}"
  local db_name="${4:-bangla_library_local_prod}"

  cat <<EOF
╔══════════════════════════════════════════════╗
║  elibrary — Local Production                 ║
╠══════════════════════════════════════════════╣
║  Branch       ${branch} $(printf '%*s' $((27 - ${#branch})) '')
║  Frontend     http://localhost:${frontend_port} $(printf '%*s' $((27 - ${#frontend_port})) '')
║  Backend      http://localhost:${backend_port} $(printf '%*s' $((27 - ${#backend_port})) '')
║  Database     ${db_name} $(printf '%*s' $((27 - ${#db_name})) '')
╚══════════════════════════════════════════════╝
EOF
}

load_config() {
  ensure_env_file "${LOCAL_PROD_DIR}/env/app.env.example" "${APP_ENV_FILE}"
  ensure_env_file "${LOCAL_PROD_DIR}/env/local_prod_config.env.example" "${CONFIG_ENV_FILE}"
  load_env_if_present "${CONFIG_ENV_FILE}"
  load_env_if_present "${APP_ENV_FILE}"

  BRANCH="${GIT_BRANCH:-main}"
  COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-elibrary-local-prod}"
  export COMPOSE_PROJECT_NAME
}

check_branch() {
  local target_branch="$1"
  local current_branch
  current_branch="$(cd "${REPO_ROOT}" && git rev-parse --abbrev-ref HEAD)"

  if [[ "${current_branch}" != "${target_branch}" ]]; then
    print_warn "Current branch is '${current_branch}', target is '${target_branch}'"
    local response
    response="$(timed_yes_no_prompt "Switch to ${target_branch}?" 10 y)"
    if [[ "${response}" == "y" ]]; then
      (cd "${REPO_ROOT}" && git checkout "${target_branch}")
    else
      print_info "Continuing with current branch: ${current_branch}"
      BRANCH="${current_branch}"
    fi
  fi
}

git_pull() {
  print_info "[2/5] Updating repository..."
  (cd "${REPO_ROOT}" && git pull origin "${BRANCH}")
}

do_build() {
  print_info "[3/5] Building Docker images..."
  compose -f "${COMPOSE_FILE}" build
}

do_up() {
  local do_pull="${1:-1}"
  local no_sleep="${2:-0}"

  print_banner \
    "${BRANCH}" \
    "${FRONTEND_PORT:-8001}" \
    "${BACKEND_PORT:-8002}" \
    "${POSTGRES_DB:-bangla_library_local_prod}"

  print_info "[1/5] Checking environment..."
  check_branch "${BRANCH}"

  if [[ "${do_pull}" == "1" ]]; then
    git_pull
  else
    print_info "[2/5] Skipping git pull (--no-pull)"
  fi

  do_build

  if [[ "${no_sleep}" == "1" ]]; then
    start_caffeinate
  fi

  print_info "[4/5] Starting services..."
  compose -f "${COMPOSE_FILE}" up -d --force-recreate "${DEFAULT_SERVICES[@]}"

  print_info "[5/5] Verifying health..."
  local backend_url="http://127.0.0.1:${BACKEND_PORT:-8002}/api/csrf/"
  local frontend_url="http://127.0.0.1:${FRONTEND_PORT:-8001}/"
  local attempts=30
  local attempt

  for attempt in $(seq 1 "${attempts}"); do
    if curl -s -o /dev/null -w '%{http_code}' --max-time 5 "${backend_url}" 2>/dev/null | grep -qv '000\|5'; then
      break
    fi
    sleep 2
  done

  for attempt in $(seq 1 "${attempts}"); do
    if curl -s -o /dev/null -w '%{http_code}' --max-time 5 "${frontend_url}" 2>/dev/null | grep -qv '000\|5'; then
      break
    fi
    sleep 2
  done

  echo
  print_info "Local production stack is running."
  echo
  echo "  Frontend:  http://localhost:${FRONTEND_PORT:-8001}"
  echo "  Backend:   http://localhost:${BACKEND_PORT:-8002}/api/csrf/"
  echo

  local admin_email="${SUPER_ADMIN_EMAIL:-admin@example.com}"
  local admin_pass="${SUPER_ADMIN_PASSWORD:-changeme}"
  print_super_admin_credentials \
    "${admin_email}" \
    "${admin_pass}" \
    "Super admin credentials"
}

parse_args() {
  COMMAND="up"
  NO_PULL=0
  NO_SLEEP=0
  BRANCH_ARG=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      up|down|restart|logs|ps)
        COMMAND="$1"
        shift
        ;;
      --branch)
        BRANCH_ARG="$2"
        shift 2
        ;;
      --no-pull)
        NO_PULL=1
        shift
        ;;
      --no-sleep)
        NO_SLEEP=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        if [[ "${COMMAND}" != "up" ]] && [[ "${COMMAND}" != "restart" ]] && [[ "${COMMAND}" != "logs" ]]; then
          usage
          die "Unsupported argument: $1"
        fi
        break
        ;;
    esac
  done

  REMAINING_ARGS=("$@")
}

main() {
  parse_args "$@"
  load_config

  if [[ -n "${BRANCH_ARG}" ]]; then
    BRANCH="${BRANCH_ARG}"
  fi

  case "${COMMAND}" in
    up)
      do_up "${NO_PULL}" "${NO_SLEEP}"
      ;;
    down)
      print_info "Stopping local production stack."
      compose -f "${COMPOSE_FILE}" down --remove-orphans
      stop_caffeinate
      ;;
    restart)
      if [[ ${#REMAINING_ARGS[@]} -gt 0 ]]; then
        compose -f "${COMPOSE_FILE}" restart "${REMAINING_ARGS[@]}"
      else
        compose -f "${COMPOSE_FILE}" restart "${DEFAULT_SERVICES[@]}"
      fi
      ;;
    logs)
      if [[ ${#REMAINING_ARGS[@]} -gt 0 ]]; then
        compose -f "${COMPOSE_FILE}" logs -f "${REMAINING_ARGS[@]}"
      else
        compose -f "${COMPOSE_FILE}" logs -f
      fi
      ;;
    ps)
      compose -f "${COMPOSE_FILE}" ps
      ;;
  esac
}

main "$@"
