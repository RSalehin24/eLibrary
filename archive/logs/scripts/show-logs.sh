#!/usr/bin/env bash

set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
source "$(cd -- "$(dirname -- "${SCRIPT_PATH}")/../.." >/dev/null 2>&1 && pwd)/automation/lib/common.sh"
REPO_ROOT="$(repo_root_from "${SCRIPT_PATH}")"
export REPO_ROOT

usage() {
  cat <<'EOF'
Usage:
  logs/scripts/show-logs.sh <frontend|backend|worker|beat> [local|remote]

Examples:
  logs/scripts/show-logs.sh frontend
  logs/scripts/show-logs.sh backend local
  logs/scripts/show-logs.sh backend remote
  logs/scripts/show-logs.sh worker remote
  logs/scripts/show-logs.sh beat remote
EOF
}

service_name="${1:-}"
target_scope="${2:-local}"
log_file=""

if [[ -z "${service_name}" || "${service_name}" == "-h" || "${service_name}" == "--help" ]]; then
  usage
  exit 0
fi

tail_local_logs() {
  local files=("$@")
  local file_path

  for file_path in "${files[@]}"; do
    prepare_log_file "${file_path}"
  done

  tail -n 200 -F "${files[@]}"
}

stream_remote_compose_logs() {
  local output_file="${1:?output file is required}"
  shift

  local compose_services=("$@")
  local compose_services_arg
  printf -v compose_services_arg '%q ' "${compose_services[@]}"
  prepare_log_file "${output_file}"

  ssh "${remote_target}" "cd '${remote_app_dir}' && bash -c 'source automation/lib/common.sh && load_env_if_present deploy/env/.app.env && if docker compose version >/dev/null 2>&1; then docker compose -f deploy/compose/docker-compose.yml logs -f ${compose_services_arg}; else docker-compose -f deploy/compose/docker-compose.yml logs -f ${compose_services_arg}; fi'" 2>&1 | tee -a "${output_file}"
}

case "${target_scope}" in
  local)
    ensure_env_file "${REPO_ROOT}/local/env/app.env.example" "${REPO_ROOT}/local/env/.env"
    if [[ "${service_name}" == "frontend" ]]; then
      tail_local_logs "${REPO_ROOT}/logs/local/frontend/frontend.log"
      exit 0
    fi

    if [[ "${service_name}" == "backend" ]]; then
      tail_local_logs \
        "${REPO_ROOT}/logs/local/backend/backend.log" \
        "${REPO_ROOT}/logs/local/celery/worker.log" \
        "${REPO_ROOT}/logs/local/celery/beat.log"
      exit 0
    fi

    if [[ "${service_name}" == "worker" ]]; then
      tail_local_logs "${REPO_ROOT}/logs/local/celery/worker.log"
      exit 0
    fi

    if [[ "${service_name}" == "beat" ]]; then
      tail_local_logs "${REPO_ROOT}/logs/local/celery/beat.log"
      exit 0
    fi

    usage
    die "Unsupported local log target: ${service_name}. Choose frontend, backend, worker, or beat."
    ;;
  remote)
    load_env_if_present "${REPO_ROOT}/deploy/env/.host.env"
    remote_user="${DEPLOY_USER_NAME:-ubuntu}"
    remote_host="${DEPLOY_IP:-}"
    remote_app_dir="${DEPLOY_REMOTE_APP_DIR:-/home/${remote_user}/library_app}"
    [[ -n "${remote_host}" ]] || die "DEPLOY_IP must be set in deploy/env/.host.env for remote logs."
    remote_target="${remote_user}@${remote_host}"
    log_file="${REPO_ROOT}/logs/remote/${service_name}/${service_name}.log"
    prepare_log_file "${log_file}"

    if [[ "${service_name}" == "frontend" ]]; then
      ssh "${remote_target}" "sudo tail -n 200 -f /var/log/nginx/access.log /var/log/nginx/error.log" 2>&1 | tee -a "${log_file}"
      exit 0
    fi

    if [[ "${service_name}" == "backend" ]]; then
      stream_remote_compose_logs "${log_file}" backend worker beat
      exit 0
    fi

    if [[ "${service_name}" == "worker" ]]; then
      stream_remote_compose_logs "${REPO_ROOT}/logs/remote/celery/worker.log" worker
      exit 0
    fi

    if [[ "${service_name}" == "beat" ]]; then
      stream_remote_compose_logs "${REPO_ROOT}/logs/remote/celery/beat.log" beat
      exit 0
    fi

    usage
    die "Unsupported remote log target: ${service_name}. Choose frontend, backend, worker, or beat."
    ;;
  *)
    usage
    die "Unsupported log scope: ${target_scope}"
    ;;
esac
