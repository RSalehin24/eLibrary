#!/usr/bin/env bash

set -euo pipefail

: "${SCRIPT_PATH:=${BASH_SOURCE[0]}}"
MIGRATION_DIR="$(cd -- "$(dirname -- "${SCRIPT_PATH}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "${MIGRATION_DIR}/.." >/dev/null 2>&1 && pwd)"
export REPO_ROOT

source "${MIGRATION_DIR}/lib/logging.sh"
source "${MIGRATION_DIR}/lib/config.sh"
source "${MIGRATION_DIR}/lib/ssh.sh"
source "${MIGRATION_DIR}/lib/bundle.sh"
source "${MIGRATION_DIR}/lib/compose.sh"

usage() {
  cat <<'EOF'
Usage:
  migration/migrate.sh [--config migration/env/migrate.env] [--phase preflight|snapshot|restore|verify|full] [--dry-run] [--resume] [--keep-staging] [--allow-target-reset] [--skip-edge]

Options:
  --config      Path to the migration config file. Defaults to migration/env/migrate.env.
  --phase       Which phase to run:
                  preflight - check SSH access, disk space, and source health (safe, no changes made)
                  snapshot  - freeze the source and capture a database + storage snapshot
                  restore   - upload the snapshot and rebuild the application on the target
                  verify    - confirm target services are healthy and optionally set up nginx/SSL
                  full      - run all phases end-to-end (default)
  --dry-run     Print what would happen without making any changes.
  --resume      Skip phases already marked as complete. Use after a partial or interrupted run.
  --keep-staging       Keep the local staging bundle on disk after a successful migration.
  --allow-target-reset Allow wiping existing data on the target before restoring.
  --skip-edge          Skip nginx and certbot setup on the target server.

Before migrating:
  1. Source server (AWS)           - deploy/env/.host.env        set DEPLOY_USER_NAME and DEPLOY_IP
  2. Target server (Digital Ocean) - migration/env/migrate.env set TARGET_USER and TARGET_IP

Examples:
  migration/migrate.sh --phase preflight --dry-run
  migration/migrate.sh --config migration/env/migrate.env --phase full
  migration/migrate.sh --phase restore --resume
EOF
}

q() {
  printf '%q' "$1"
}

CONFIG_FILE="${MIGRATION_DIR}/env/migrate.env"
CONFIG_EXAMPLE_FILE="${MIGRATION_DIR}/env/migrate.env.example"
PHASE="full"
DRY_RUN=0
RESUME=0
KEEP_STAGING_FLAG=""
ALLOW_TARGET_RESET_FLAG=""
SKIP_EDGE_FLAG=""
SOURCE_FROZEN=0
SOURCE_RESTARTED=0
EDGE_SETUP_READY=0
EDGE_SETUP_REASON="disabled"
FINAL_SUCCESS=0

APP_ARCHIVE_FILE=""
STORAGE_ARCHIVE_FILE=""
POSTGRES_DUMP_FILE=""
REDIS_DUMP_FILE=""
APP_ENV_BUNDLE_FILE=""
TARGET_OVERRIDE_FILE=""
METADATA_FILE=""
CHECKSUMS_FILE=""
LOG_FILE=""

apply_deploy_defaults() {
  local deploy_host_env_file="${REPO_ROOT}/deploy/env/.host.env"
  local deploy_user=""
  local deploy_ip=""
  local deploy_remote_app_dir=""
  local deploy_domain=""
  local deploy_certbot_email=""
  local deploy_backend_port=""
  local deploy_frontend_port=""
  local deploy_docker_version=""
  local deploy_nginx_version=""
  local deploy_nginx_conf_dir=""
  local deploy_nginx_config_name=""

  if [[ -f "${deploy_host_env_file}" ]]; then
    deploy_user="$(read_env_value_from_file "${deploy_host_env_file}" "DEPLOY_USER_NAME")"
    deploy_ip="$(read_env_value_from_file "${deploy_host_env_file}" "DEPLOY_IP")"
    deploy_remote_app_dir="$(read_env_value_from_file "${deploy_host_env_file}" "DEPLOY_REMOTE_APP_DIR")"
    deploy_domain="$(read_env_value_from_file "${deploy_host_env_file}" "DEPLOY_DOMAIN")"
    deploy_certbot_email="$(read_env_value_from_file "${deploy_host_env_file}" "DEPLOY_CERTBOT_EMAIL")"
    deploy_backend_port="$(read_env_value_from_file "${deploy_host_env_file}" "BACKEND_PORT")"
    deploy_frontend_port="$(read_env_value_from_file "${deploy_host_env_file}" "FRONTEND_PORT")"
    deploy_docker_version="$(read_env_value_from_file "${deploy_host_env_file}" "DEPLOY_DOCKER_VERSION")"
    deploy_nginx_version="$(read_env_value_from_file "${deploy_host_env_file}" "DEPLOY_NGINX_VERSION")"
    deploy_nginx_conf_dir="$(read_env_value_from_file "${deploy_host_env_file}" "DEPLOY_NGINX_CONF_DIR")"
    deploy_nginx_config_name="$(read_env_value_from_file "${deploy_host_env_file}" "DEPLOY_NGINX_CONFIG_NAME")"
  fi

  default_if_empty SOURCE_HOST "${deploy_ip}"
  default_if_empty SOURCE_USER "${deploy_user}"
  if [[ -n "${deploy_remote_app_dir}" ]]; then
    default_if_empty SOURCE_REMOTE_APP_DIR "${deploy_remote_app_dir}"
  fi

  default_if_empty TARGET_USER "${deploy_user}"
  default_if_empty TARGET_REMOTE_APP_DIR "${deploy_remote_app_dir}"
  default_if_empty TARGET_DOMAIN "${deploy_domain}"
  default_if_empty TARGET_CERTBOT_EMAIL "${deploy_certbot_email}"
  default_if_empty BACKEND_PORT "${deploy_backend_port}"
  default_if_empty FRONTEND_PORT "${deploy_frontend_port}"
  default_if_empty DEPLOY_DOCKER_VERSION "${deploy_docker_version}"
  default_if_empty DEPLOY_NGINX_VERSION "${deploy_nginx_version}"
  default_if_empty DEPLOY_NGINX_CONF_DIR "${deploy_nginx_conf_dir}"
  default_if_empty DEPLOY_NGINX_CONFIG_NAME "${deploy_nginx_config_name}"
}

log_layout_defaults() {
  if [[ "${TARGET_REMOTE_APP_DIR}" == "${SOURCE_REMOTE_APP_DIR}" ]]; then
    log_info "The application will use the same folder path and repository structure on the new server: ${TARGET_REMOTE_APP_DIR}"
  else
    log_info "The target application path is overridden to ${TARGET_REMOTE_APP_DIR}"
  fi
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --config)
        CONFIG_FILE="${2:?--config requires a value}"
        shift 2
        ;;
      --phase)
        PHASE="${2:?--phase requires a value}"
        shift 2
        ;;
      --dry-run)
        DRY_RUN=1
        shift
        ;;
      --resume)
        RESUME=1
        shift
        ;;
      --keep-staging)
        KEEP_STAGING_FLAG="1"
        shift
        ;;
      --allow-target-reset)
        ALLOW_TARGET_RESET_FLAG="1"
        shift
        ;;
      --skip-edge)
        SKIP_EDGE_FLAG="1"
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        usage
        die "Unsupported argument: $1"
        ;;
    esac
  done

  case "${PHASE}" in
    preflight|snapshot|restore|verify|full)
      ;;
    *)
      die "Unsupported phase: ${PHASE}"
      ;;
  esac
}

initialize_config() {
  ensure_config_file "${CONFIG_EXAMPLE_FILE}" "${CONFIG_FILE}"
  load_config_file "${CONFIG_FILE}"

  default_if_empty SOURCE_PORT "22"
  default_if_empty TARGET_PORT "22"
  apply_deploy_defaults
  default_if_empty SOURCE_USER "ubuntu"
  default_if_empty SOURCE_REMOTE_APP_DIR "/home/${SOURCE_USER}/library_app"
  default_if_empty TARGET_USER "${SOURCE_USER}"
  default_if_empty TARGET_REMOTE_APP_DIR "${SOURCE_REMOTE_APP_DIR}"
  default_if_empty BACKEND_PORT "8000"
  default_if_empty FRONTEND_PORT "4173"
  default_if_empty DEPLOY_NGINX_VERSION "1.29.4"
  default_if_empty DEPLOY_NGINX_CONF_DIR "/etc/nginx/conf.d"
  default_if_empty STRICT_HOST_KEY_MODE "accept-new"
  default_if_empty LOCAL_STAGING_DIR "${MIGRATION_DIR}/runtime"
  default_if_empty DRAIN_TIMEOUT_SECONDS "900"
  default_if_empty HEALTHCHECK_TIMEOUT_SECONDS "240"
  default_if_empty KEEP_SOURCE_DOWN_ON_SUCCESS "0"
  default_if_empty ALLOW_TARGET_RESET "0"
  default_if_empty SKIP_EDGE_SETUP "0"
  default_if_empty KEEP_STAGING "1"

  normalize_bool_var KEEP_SOURCE_DOWN_ON_SUCCESS "0"
  normalize_bool_var ALLOW_TARGET_RESET "0"
  normalize_bool_var SKIP_EDGE_SETUP "0"
  normalize_bool_var KEEP_STAGING "1"

  if [[ -n "${KEEP_STAGING_FLAG}" ]]; then
    KEEP_STAGING=1
  fi
  if [[ -n "${ALLOW_TARGET_RESET_FLAG}" ]]; then
    ALLOW_TARGET_RESET=1
  fi
  if [[ -n "${SKIP_EDGE_FLAG}" ]]; then
    SKIP_EDGE_SETUP=1
  fi

  if [[ -z "${DEPLOY_NGINX_CONFIG_NAME:-}" && -n "${TARGET_DOMAIN:-}" ]]; then
    DEPLOY_NGINX_CONFIG_NAME="${TARGET_DOMAIN}.conf"
  fi

  mkdir -p "${LOCAL_STAGING_DIR}"

  if [[ -z "${BUNDLE_ID:-}" ]]; then
    if [[ "${RESUME}" == "1" ]]; then
      BUNDLE_ID="$(latest_bundle_id "${LOCAL_STAGING_DIR}")"
    else
      BUNDLE_ID="migration-$(date -u +%Y%m%d-%H%M%S)"
    fi
  fi

  [[ -n "${BUNDLE_ID}" ]] || die "Unable to determine BUNDLE_ID. Set it in the config or create a bundle first."

  BUNDLE_DIR="${LOCAL_STAGING_DIR}/${BUNDLE_ID}"
  mkdir -p "${BUNDLE_DIR}"

  LOG_FILE="${BUNDLE_DIR}/migration.log"
  touch "${LOG_FILE}"

  APP_ARCHIVE_FILE="${BUNDLE_DIR}/app.tar.gz"
  STORAGE_ARCHIVE_FILE="${BUNDLE_DIR}/storage.tar.gz"
  POSTGRES_DUMP_FILE="${BUNDLE_DIR}/postgres.sql.gz"
  REDIS_DUMP_FILE="${BUNDLE_DIR}/redis-dump.rdb"
  APP_ENV_BUNDLE_FILE="${BUNDLE_DIR}/app.env"
  TARGET_OVERRIDE_FILE="${BUNDLE_DIR}/target-env-overrides.env"
  METADATA_FILE="${BUNDLE_DIR}/metadata.env"
  CHECKSUMS_FILE="${BUNDLE_DIR}/checksums.sha256"
  TARGET_REMOTE_BUNDLE_DIR="/tmp/${BUNDLE_ID}"
  TARGET_RESET_ALLOWED=0

  if [[ "${RESUME}" == "1" && ! -d "${BUNDLE_DIR}" ]]; then
    die "No previous migration run found. Remove --resume to start a new migration."
  fi

  log_layout_defaults
}

validate_required_config() {
  local required_keys=(
    SOURCE_HOST
    SOURCE_USER
    SOURCE_REMOTE_APP_DIR
    TARGET_IP
    TARGET_USER
    TARGET_REMOTE_APP_DIR
    TARGET_IP
  )
  local key
  for key in "${required_keys[@]}"; do
    [[ -n "${!key:-}" ]] || die "Set ${key} in ${CONFIG_FILE} and retry."
  done
}

