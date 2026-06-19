#!/usr/bin/env bash

set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
source "$(cd -- "$(dirname -- "${SCRIPT_PATH}")/../.." >/dev/null 2>&1 && pwd)/automation/lib/common.sh"
REPO_ROOT="$(repo_root_from "${SCRIPT_PATH}")"
export REPO_ROOT

APP_ENV_FILE="${REPO_ROOT}/local/env/.env"
COMPOSE_ARGS=(-f "${REPO_ROOT}/local/compose/docker-compose.yml")
DEFAULT_SERVICES=(postgres redis backend worker processing-worker beat engine frontend)

usage() {
  cat <<'EOF'
Usage:
  local/scripts/dev.sh [up|down|restart|logs|ps] [service...]

Examples:
  local/scripts/dev.sh
  local/scripts/dev.sh up
  LOCALHOST_ONLY=1 local/scripts/dev.sh up
  local/scripts/dev.sh logs backend
  local/scripts/dev.sh down

Every non-help run prints the effective local super admin email and password.
EOF
}

detect_default_interface() {
  route -n get default 2>/dev/null | awk '/interface:/{print $2; exit}'
}

detect_lan_ip() {
  local interface_name="${RUN_LOCAL_INTERFACE:-}"
  local lan_ip=""

  if [[ -z "${interface_name}" ]]; then
    interface_name="$(detect_default_interface || true)"
  fi

  if [[ -n "${interface_name}" ]]; then
    lan_ip="$(ipconfig getifaddr "${interface_name}" 2>/dev/null || true)"
  fi

  if [[ -z "${lan_ip}" ]]; then
    for interface_name in en0 en1; do
      lan_ip="$(ipconfig getifaddr "${interface_name}" 2>/dev/null || true)"
      if [[ -n "${lan_ip}" ]]; then
        break
      fi
    done
  fi

  if [[ -z "${lan_ip}" ]]; then
    lan_ip="$(ifconfig | awk '/inet / && $2 != "127.0.0.1" {print $2; exit}' || true)"
  fi

  printf '%s' "${lan_ip}"
}

command_name="${1:-up}"
if [[ $# -gt 0 ]]; then
  shift
fi

ensure_env_file "${REPO_ROOT}/local/env/app.env.example" "${APP_ENV_FILE}"
load_env_if_present "${APP_ENV_FILE}"

LAN_IP_EFFECTIVE=""
LOCALHOST_ONLY_ENABLED="${LOCALHOST_ONLY:-0}"
if [[ "${command_name}" == "up" ]]; then
  if [[ "${LOCALHOST_ONLY_ENABLED}" == "1" || "${LOCALHOST_ONLY_ENABLED}" == "true" || "${LOCALHOST_ONLY_ENABLED}" == "yes" ]]; then
    export HOST_BIND_IP="127.0.0.1"
  else
    LAN_IP_EFFECTIVE="$(detect_lan_ip)"
    if [[ -n "${LAN_IP_EFFECTIVE}" ]]; then
      export HOST_BIND_IP="0.0.0.0"
      export PUBLIC_BASE_URL="http://${LAN_IP_EFFECTIVE}:${BACKEND_PORT:-8000}"
      export PUBLIC_API_ORIGIN="http://${LAN_IP_EFFECTIVE}:${BACKEND_PORT:-8000}"
      export FRONTEND_BASE_URL="http://${LAN_IP_EFFECTIVE}:${FRONTEND_PORT:-5173}"
    else
      print_warn "Unable to detect a LAN IP address. Falling back to localhost-only access."
      export HOST_BIND_IP="127.0.0.1"
    fi
  fi
fi

SUPER_ADMIN_EMAIL_EFFECTIVE="$(effective_env_value SUPER_ADMIN_EMAIL "admin@example.com")"
SUPER_ADMIN_PASSWORD_EFFECTIVE="$(effective_env_value SUPER_ADMIN_PASSWORD "changeme")"
FRONTEND_URL_EFFECTIVE="$(effective_env_value FRONTEND_BASE_URL "http://127.0.0.1:${FRONTEND_PORT:-5173}")"
BACKEND_URL_EFFECTIVE="$(effective_env_value PUBLIC_API_ORIGIN "http://127.0.0.1:${BACKEND_PORT:-8000}")"

if [[ "${command_name}" != "-h" && "${command_name}" != "--help" && "${command_name}" != "help" ]]; then
  print_super_admin_credentials \
    "${SUPER_ADMIN_EMAIL_EFFECTIVE}" \
    "${SUPER_ADMIN_PASSWORD_EFFECTIVE}" \
    "Local super admin credentials" \
    "Keep these credentials available for local access and browser testing."
fi

case "${command_name}" in
  up)
    print_info "Starting local development stack with Docker Compose watch enabled."
    if [[ -n "${LAN_IP_EFFECTIVE}" ]]; then
      print_info "Network access enabled on ${LAN_IP_EFFECTIVE}. Use the printed frontend URL from another device on the same network."
    elif [[ "${HOST_BIND_IP:-127.0.0.1}" == "127.0.0.1" ]]; then
      print_info "Localhost-only access enabled."
    fi
    compose "${COMPOSE_ARGS[@]}" up --build --watch "${DEFAULT_SERVICES[@]}" "$@"
    cat <<EOF
Local development stack is running.

Frontend: ${FRONTEND_URL_EFFECTIVE}
Backend:  ${BACKEND_URL_EFFECTIVE}

Use:
  local/scripts/dev.sh logs frontend
  local/scripts/dev.sh logs backend
  local/scripts/dev.sh down
EOF
    ;;
  down)
    print_info "Stopping local development stack."
    compose "${COMPOSE_ARGS[@]}" down --remove-orphans
    ;;
  restart)
    print_info "Restarting selected services."
    if [[ $# -gt 0 ]]; then
      compose "${COMPOSE_ARGS[@]}" restart "$@"
    else
      compose "${COMPOSE_ARGS[@]}" restart "${DEFAULT_SERVICES[@]}"
    fi
    ;;
  logs)
    if [[ $# -eq 0 ]]; then
      usage
      die "Select a service group for logs: frontend or backend"
    fi
    service_group="$(service_group_for_logs "$1")" || die "Unsupported service group: $1"
    # shellcheck disable=SC2086
    compose "${COMPOSE_ARGS[@]}" logs -f ${service_group}
    ;;
  ps)
    compose "${COMPOSE_ARGS[@]}" ps
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage
    die "Unsupported command: ${command_name}"
    ;;
esac
