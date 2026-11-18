ensure_target_docker() {
  log_info "Ensuring Docker is available on target."
  local needs_install
  needs_install="$(remote_run target "$(cat <<EOF
if ! command -v docker >/dev/null 2>&1; then
  echo yes
elif ! docker compose version >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
  echo yes
elif [[ -n $(q "${DEPLOY_DOCKER_VERSION:-}") ]] && ! docker --version | grep -Fq $(q "${DEPLOY_DOCKER_VERSION:-}"); then
  echo yes
else
  echo no
fi
EOF
)")"
  if [[ "${needs_install}" == "yes" ]]; then
    remote_sudo target "cd $(q "${TARGET_REMOTE_APP_DIR}") && bash deploy/scripts/install-docker.sh $(q "${DEPLOY_DOCKER_VERSION:-}")"
  fi
}

target_compose_reset() {
  remote_run target "$(compose_remote_script "${TARGET_REMOTE_APP_DIR}" "$(cat <<'EOF'
compose "${COMPOSE_ARGS[@]}" down --volumes --remove-orphans || true
compose "${COMPOSE_ARGS[@]}" up -d postgres redis
EOF
)")"
}

wait_for_target_core_services() {
  log_info "Waiting for target postgres and redis."
  local deadline=$(( $(date +%s) + HEALTHCHECK_TIMEOUT_SECONDS ))
  while true; do
    if remote_run target "$(compose_remote_script "${TARGET_REMOTE_APP_DIR}" "$(cat <<'EOF'
compose "${COMPOSE_ARGS[@]}" exec -T postgres pg_isready -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-bangla_library}" >/dev/null
compose "${COMPOSE_ARGS[@]}" exec -T redis redis-cli ping | grep -Fq PONG
EOF
)")" >/dev/null 2>&1; then
      return 0
    fi
    if (( $(date +%s) >= deadline )); then
      die "Timed out waiting for target postgres/redis."
    fi
    sleep 5
  done
}

restore_target_postgres() {
  log_info "Restoring PostgreSQL cluster on target."
  remote_run target "$(compose_remote_script "${TARGET_REMOTE_APP_DIR}" "$(cat <<EOF
gunzip -c $(q "${TARGET_REMOTE_BUNDLE_DIR}/postgres.sql.gz") | compose "\${COMPOSE_ARGS[@]}" exec -T postgres psql -v ON_ERROR_STOP=1 -U "\${POSTGRES_USER:-postgres}" -d postgres
EOF
)")"
}

restore_target_redis() {
  log_info "Restoring Redis dump on target."
  remote_run target "$(compose_remote_script "${TARGET_REMOTE_APP_DIR}" "$(cat <<EOF
compose "\${COMPOSE_ARGS[@]}" stop redis
container_id="\$(compose "\${COMPOSE_ARGS[@]}" ps -q redis)"
docker cp $(q "${TARGET_REMOTE_BUNDLE_DIR}/redis-dump.rdb") "\${container_id}:/data/dump.rdb"
compose "\${COMPOSE_ARGS[@]}" start redis
compose "\${COMPOSE_ARGS[@]}" exec -T redis redis-cli ping | grep -Fq PONG
EOF
)")"
}

restore_target_storage() {
  log_info "Restoring storage tree on target."
  remote_run target "$(cat <<EOF
mkdir -p $(q "${TARGET_REMOTE_APP_DIR}/app/backend")
tar -xzf $(q "${TARGET_REMOTE_BUNDLE_DIR}/storage.tar.gz") -C $(q "${TARGET_REMOTE_APP_DIR}/app/backend")
EOF
)"
  remote_sudo target "chown -R $(q "${TARGET_USER}:${TARGET_USER}") $(q "${TARGET_REMOTE_APP_DIR}/app/backend/storage") && chmod -R u+rwX,go+rX $(q "${TARGET_REMOTE_APP_DIR}/app/backend/storage")"
}

compare_summary_value() {
  local label="${1:?label is required}"
  local source_value="${2:-}"
  local target_value="${3:-}"
  if [[ "${source_value}" != "${target_value}" ]]; then
    die "Summary mismatch for ${label}: source=${source_value} target=${target_value}"
  fi
}

capture_target_prestart_summary() {
  local db_summary redis_summary storage_summary
  db_summary="$(capture_db_summary target "${TARGET_REMOTE_APP_DIR}")"
  redis_summary="$(capture_redis_summary target "${TARGET_REMOTE_APP_DIR}")"
  storage_summary="$(capture_storage_summary target "${TARGET_REMOTE_APP_DIR}/app/backend/storage")"

  local DB_TABLE_COUNT="" DB_ROW_TOTAL="" DB_ROLE_COUNT="" DB_TABLE_ROWS_SHA256=""
  local REDIS_DBSIZE="" REDIS_QUEUE_CELERY="" REDIS_QUEUE_PROCESSING="" REDIS_USED_MEMORY=""
  local STORAGE_FILE_COUNT="" STORAGE_TOTAL_BYTES=""

  while IFS='=' read -r key value; do
    [[ -n "${key}" ]] || continue
    printf -v "${key}" '%s' "${value}"
  done <<<"${db_summary}"$'\n'"${redis_summary}"$'\n'"${storage_summary}"

  compare_summary_value DB_TABLE_COUNT "${SOURCE_DB_TABLE_COUNT}" "${DB_TABLE_COUNT}"
  compare_summary_value DB_ROW_TOTAL "${SOURCE_DB_ROW_TOTAL}" "${DB_ROW_TOTAL}"
  compare_summary_value DB_ROLE_COUNT "${SOURCE_DB_ROLE_COUNT}" "${DB_ROLE_COUNT}"
  compare_summary_value DB_TABLE_ROWS_SHA256 "${SOURCE_DB_TABLE_ROWS_SHA256}" "${DB_TABLE_ROWS_SHA256}"
  compare_summary_value REDIS_DBSIZE "${SOURCE_REDIS_DBSIZE}" "${REDIS_DBSIZE}"
  compare_summary_value REDIS_QUEUE_CELERY "${SOURCE_REDIS_QUEUE_CELERY}" "${REDIS_QUEUE_CELERY}"
  compare_summary_value REDIS_QUEUE_PROCESSING "${SOURCE_REDIS_QUEUE_PROCESSING}" "${REDIS_QUEUE_PROCESSING}"
  compare_summary_value STORAGE_FILE_COUNT "${SOURCE_STORAGE_FILE_COUNT}" "${STORAGE_FILE_COUNT}"
  compare_summary_value STORAGE_TOTAL_BYTES "${SOURCE_STORAGE_TOTAL_BYTES}" "${STORAGE_TOTAL_BYTES}"

  append_metadata TARGET_PRESTART_DB_TABLE_COUNT "${DB_TABLE_COUNT}"
  append_metadata TARGET_PRESTART_DB_ROW_TOTAL "${DB_ROW_TOTAL}"
  append_metadata TARGET_PRESTART_DB_ROLE_COUNT "${DB_ROLE_COUNT}"
  append_metadata TARGET_PRESTART_DB_TABLE_ROWS_SHA256 "${DB_TABLE_ROWS_SHA256}"
  append_metadata TARGET_PRESTART_REDIS_DBSIZE "${REDIS_DBSIZE}"
  append_metadata TARGET_PRESTART_REDIS_QUEUE_CELERY "${REDIS_QUEUE_CELERY}"
  append_metadata TARGET_PRESTART_REDIS_QUEUE_PROCESSING "${REDIS_QUEUE_PROCESSING}"
  append_metadata TARGET_PRESTART_STORAGE_FILE_COUNT "${STORAGE_FILE_COUNT}"
  append_metadata TARGET_PRESTART_STORAGE_TOTAL_BYTES "${STORAGE_TOTAL_BYTES}"
  append_metadata TARGET_PRESTART_SUMMARY_MATCH "1"
}

wait_for_backend_init() {
  log_info "Running backend-init on target."
  remote_run target "$(compose_remote_script "${TARGET_REMOTE_APP_DIR}" "$(cat <<'EOF'
compose "${COMPOSE_ARGS[@]}" up -d backend-init
EOF
)")"

  local deadline=$(( $(date +%s) + HEALTHCHECK_TIMEOUT_SECONDS ))
  while true; do
    local status exit_code
    status="$(remote_run target "$(compose_remote_script "${TARGET_REMOTE_APP_DIR}" "$(cat <<'EOF'
container_id="$(compose "${COMPOSE_ARGS[@]}" ps -q backend-init)"
docker inspect -f '{{.State.Status}}' "${container_id}"
EOF
)")")"
    if [[ "${status}" == "exited" ]]; then
      exit_code="$(remote_run target "$(compose_remote_script "${TARGET_REMOTE_APP_DIR}" "$(cat <<'EOF'
container_id="$(compose "${COMPOSE_ARGS[@]}" ps -q backend-init)"
docker inspect -f '{{.State.ExitCode}}' "${container_id}"
EOF
)")")"
      [[ "${exit_code}" == "0" ]] || die "The backend failed to initialise on the target server. Check the container logs on the target, fix the issue, and retry with --phase restore --resume."
      return 0
    fi
    if (( $(date +%s) >= deadline )); then
      die "The backend initialisation timed out on the target server. Check the container logs on the target and retry with --phase restore --resume."
    fi
    sleep 5
  done
}

start_target_application() {
  log_info "Starting target application services."
  remote_run target "$(compose_remote_script "${TARGET_REMOTE_APP_DIR}" "$(cat <<'EOF'
compose "${COMPOSE_ARGS[@]}" up -d backend frontend worker processing-worker beat
EOF
)")"
}

run_restore() {
  verify_bundle_ready_for_restore
  if [[ "${DRY_RUN}" == "1" ]]; then
    log_info "DRY RUN: restore would upload bundle and recreate the target stack."
    mark_phase_done restore
    return 0
  fi

  upload_bundle_to_target
  verify_remote_bundle_checksums
  prepare_target_app_directory
  extract_target_app_bundle
  ensure_target_docker
  target_compose_reset
  wait_for_target_core_services
  restore_target_postgres
  restore_target_redis
  restore_target_storage
  capture_target_prestart_summary
  wait_for_backend_init
  start_target_application
  mark_phase_done restore
  log_info "Restore completed."
}

target_service_health_check() {
  local verify_script
  verify_script="$(cat <<EOF
$(container_status_report_script)
service_status postgres 1
service_status redis 1
service_status backend 1
service_status frontend 0
service_status worker 0
service_status processing-worker 0
service_status beat 0
python3 - <<'PY'
import os
import urllib.request

backend_port = os.environ.get("BACKEND_PORT", "${BACKEND_PORT}")
frontend_port = os.environ.get("FRONTEND_PORT", "${FRONTEND_PORT}")
urllib.request.urlopen(f"http://127.0.0.1:{backend_port}/api/csrf/", timeout=20)
urllib.request.urlopen(f"http://127.0.0.1:{frontend_port}/", timeout=20)
print("ok")
PY
EOF
)"
  remote_run target "$(compose_remote_script "${TARGET_REMOTE_APP_DIR}" "${verify_script}")" >/dev/null
}

verify_target_live_summaries() {
  local live_db_summary live_storage_summary
  live_db_summary="$(capture_db_summary target "${TARGET_REMOTE_APP_DIR}")"
  live_storage_summary="$(capture_storage_summary target "${TARGET_REMOTE_APP_DIR}/app/backend/storage")"

  local DB_TABLE_COUNT="" DB_ROW_TOTAL="" DB_ROLE_COUNT="" DB_TABLE_ROWS_SHA256="" STORAGE_FILE_COUNT="" STORAGE_TOTAL_BYTES=""
  while IFS='=' read -r key value; do
    case "${key}" in
      DB_TABLE_COUNT|DB_ROW_TOTAL|DB_ROLE_COUNT|DB_TABLE_ROWS_SHA256|STORAGE_FILE_COUNT|STORAGE_TOTAL_BYTES)
        printf -v "${key}" '%s' "${value}"
        ;;
    esac
  done <<<"${live_db_summary}"$'\n'"${live_storage_summary}"

  compare_summary_value LIVE_DB_TABLE_COUNT "${SOURCE_DB_TABLE_COUNT}" "${DB_TABLE_COUNT}"
  compare_summary_value LIVE_DB_ROW_TOTAL "${SOURCE_DB_ROW_TOTAL}" "${DB_ROW_TOTAL}"
  compare_summary_value LIVE_DB_ROLE_COUNT "${SOURCE_DB_ROLE_COUNT}" "${DB_ROLE_COUNT}"
  compare_summary_value LIVE_DB_TABLE_ROWS_SHA256 "${SOURCE_DB_TABLE_ROWS_SHA256}" "${DB_TABLE_ROWS_SHA256}"
  compare_summary_value LIVE_STORAGE_FILE_COUNT "${SOURCE_STORAGE_FILE_COUNT}" "${STORAGE_FILE_COUNT}"
  compare_summary_value LIVE_STORAGE_TOTAL_BYTES "${SOURCE_STORAGE_TOTAL_BYTES}" "${STORAGE_TOTAL_BYTES}"
}

