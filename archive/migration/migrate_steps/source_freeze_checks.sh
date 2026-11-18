source_size_metrics() {
  remote_run source "$(cat <<EOF
python3 - "${SOURCE_REMOTE_APP_DIR}" <<'PY'
import os
import subprocess
import sys

app_dir = sys.argv[1]

def run_du(path, exclude_storage=False):
    cmd = ["du", "-sk"]
    if exclude_storage:
        cmd.append("--exclude=app/backend/storage")
    cmd.append(path)
    result = subprocess.check_output(cmd, text=True)
    return int(result.split()[0])

print("APP_KB={}".format(run_du(app_dir, exclude_storage=True)))
print("STORAGE_KB={}".format(run_du(os.path.join(app_dir, "app/backend/storage"))))
PY
EOF
)"
}

postgres_data_kb() {
  remote_run source "$(compose_remote_script "${SOURCE_REMOTE_APP_DIR}" "$(cat <<'EOF'
compose "${COMPOSE_ARGS[@]}" exec -T postgres sh -lc 'du -sk /var/lib/postgresql/data | awk "{print \$1}"'
EOF
)")"
}

redis_data_kb() {
  remote_run source "$(compose_remote_script "${SOURCE_REMOTE_APP_DIR}" "$(cat <<'EOF'
compose "${COMPOSE_ARGS[@]}" exec -T redis sh -lc 'du -sk /data | awk "{print \$1}"'
EOF
)")"
}

disk_space_check() {
  local source_sizes pg_kb redis_kb
  source_sizes="$(source_size_metrics)"
  pg_kb="$(postgres_data_kb)"
  redis_kb="$(redis_data_kb)"

  local source_app_kb=0 source_storage_kb=0
  while IFS='=' read -r key value; do
    case "${key}" in
      APP_KB) source_app_kb="${value}" ;;
      STORAGE_KB) source_storage_kb="${value}" ;;
    esac
  done <<<"${source_sizes}"

  local raw_total_kb=$((source_app_kb + source_storage_kb + pg_kb + redis_kb))
  local local_required_kb=$((raw_total_kb + (raw_total_kb / 4) + 102400))
  local target_required_kb=$((raw_total_kb * 2 + 102400))

  local local_free_kb target_free_kb
  local_free_kb="$(free_kb_for_path "${LOCAL_STAGING_DIR}")"
  target_free_kb="$(remote_run target "df -Pk $(q "$(dirname -- "${TARGET_REMOTE_APP_DIR}")") | awk 'NR==2 {print \$4}'")"

  [[ "${local_free_kb}" =~ ^[0-9]+$ ]] || die "Could not check local disk space. Make sure ${LOCAL_STAGING_DIR} exists and is accessible, then retry."
  [[ "${target_free_kb}" =~ ^[0-9]+$ ]] || die "Could not check disk space on the target server. Verify the target is reachable via SSH and retry."

  if (( local_free_kb < local_required_kb )); then
    die "Not enough free disk space on this machine to stage the migration. Free up space in ${LOCAL_STAGING_DIR} and retry."
  fi
  if (( target_free_kb < target_required_kb )); then
    die "Not enough free disk space on the target server. Free up space on the target and retry."
  fi
}

run_preflight() {
  log_info "Running migration preflight checks."
  validate_required_config
  require_local_tools
  remote_connectivity_check source
  remote_connectivity_check target
  if ! maybe_prompt_for_cloudflare_change; then
    log_warn "The domain confirmation was not acknowledged. Migration will continue, but edge setup may be skipped until DNS points at the target host."
  fi
  remote_os_check source
  remote_os_check target
  remote_sudo_check source
  remote_sudo_check target
  source_layout_check
  source_stack_health_check
  target_ports_check
  target_directory_state_check
  disk_space_check
  preflight_edge_setup
  write_target_override_bundle
  mark_phase_done preflight
  log_info "Preflight completed."
}

restart_source_stack() {
  log_info "Starting source services again."
  if [[ "${DRY_RUN}" == "1" ]]; then
    log_info "DRY RUN: skipping source restart."
    SOURCE_RESTARTED=1
    SOURCE_FROZEN=0
    return 0
  fi

  remote_run source "$(compose_remote_script "${SOURCE_REMOTE_APP_DIR}" "$(cat <<'EOF'
compose "${COMPOSE_ARGS[@]}" up -d backend frontend worker processing-worker beat
EOF
)")"
  SOURCE_RESTARTED=1
  SOURCE_FROZEN=0
}

freeze_source_stack() {
  SOURCE_FROZEN=1
  log_info "Stopping source beat, backend, and frontend to freeze writes."
  remote_run source "$(compose_remote_script "${SOURCE_REMOTE_APP_DIR}" "$(cat <<'EOF'
compose "${COMPOSE_ARGS[@]}" stop beat frontend backend
EOF
)")"
}

source_drain_report() {
  remote_run source "$(compose_remote_script "${SOURCE_REMOTE_APP_DIR}" "$(cat <<'EOF'
cat <<'PY' | compose "${COMPOSE_ARGS[@]}" exec -T worker python
from config.celery import app

def count_entries(payload):
    total = 0
    for entries in (payload or {}).values():
        total += len(entries or [])
    return total

inspect = app.control.inspect(timeout=2.0)
active = count_entries(inspect.active())
reserved = count_entries(inspect.reserved())
scheduled = count_entries(inspect.scheduled())
print(f"ACTIVE={active}")
print(f"RESERVED={reserved}")
print(f"SCHEDULED={scheduled}")
PY
printf 'QUEUE_CELERY=%s\n' "$(compose "${COMPOSE_ARGS[@]}" exec -T redis redis-cli --raw LLEN celery)"
printf 'QUEUE_PROCESSING=%s\n' "$(compose "${COMPOSE_ARGS[@]}" exec -T redis redis-cli --raw LLEN processing)"
EOF
)")"
}

wait_for_source_drain() {
  log_info "Waiting for source workers and queues to drain."
  local started_at now elapsed
  started_at="$(date +%s)"

  while true; do
    local report active=1 reserved=1 scheduled=1 queue_celery=1 queue_processing=1
    report="$(source_drain_report)"
    while IFS='=' read -r key value; do
      case "${key}" in
        ACTIVE) active="${value}" ;;
        RESERVED) reserved="${value}" ;;
        SCHEDULED) scheduled="${value}" ;;
        QUEUE_CELERY) queue_celery="${value}" ;;
        QUEUE_PROCESSING) queue_processing="${value}" ;;
      esac
    done <<<"${report}"

    if [[ "${active}" == "0" && "${reserved}" == "0" && "${scheduled}" == "0" && "${queue_celery}" == "0" && "${queue_processing}" == "0" ]]; then
      log_info "Source queues are drained."
      return 0
    fi

    now="$(date +%s)"
    elapsed=$((now - started_at))
    if (( elapsed >= DRAIN_TIMEOUT_SECONDS )); then
      restart_source_stack
      die "The source server queues did not drain in time. Wait for active jobs to finish and retry with --resume."
    fi

    sleep 5
  done
}

stop_source_workers() {
  log_info "Stopping source workers after drain."
  remote_run source "$(compose_remote_script "${SOURCE_REMOTE_APP_DIR}" "$(cat <<'EOF'
compose "${COMPOSE_ARGS[@]}" stop worker processing-worker
EOF
)")"
}

capture_source_env() {
  log_info "Capturing source deploy env."
  run_scp_from source "$(q "${SOURCE_REMOTE_APP_DIR}/deploy/env/.app.env")" "${APP_ENV_BUNDLE_FILE}"
}

capture_source_app_archive() {
  log_info "Streaming source application snapshot."
  run_ssh source "$(app_remote_script "${SOURCE_REMOTE_APP_DIR}" "$(cat <<'EOF'
tar -czf - \
  --exclude=.git \
  --exclude=app/backend/storage \
  --exclude=deploy/env/.app.env \
  --exclude=deploy/env/.app.compose.env \
  --exclude=app/frontend/node_modules \
  --exclude=app/frontend/dist \
  --exclude=app/frontend/test-results \
  --exclude=app/frontend/test-artifacts \
  --exclude=test-artifacts \
  --exclude=logs/local/*.log \
  --exclude=logs/remote/*.log \
  --exclude=migration/runtime \
  .
EOF
)")" >"${APP_ARCHIVE_FILE}"
}

capture_source_storage_archive() {
  log_info "Streaming source storage snapshot."
  run_ssh source "$(app_remote_script "${SOURCE_REMOTE_APP_DIR}/app/backend" "$(cat <<'EOF'
tar -czf - storage
EOF
)")" >"${STORAGE_ARCHIVE_FILE}"
}

capture_source_postgres_dump() {
  log_info "Streaming PostgreSQL cluster dump."
  run_ssh source "$(compose_remote_script "${SOURCE_REMOTE_APP_DIR}" "$(cat <<'EOF'
{
  compose "${COMPOSE_ARGS[@]}" exec -T postgres sh -c '
    pg_dumpall --globals-only -U "${POSTGRES_USER:-postgres}"
  '
  compose "${COMPOSE_ARGS[@]}" exec -T postgres sh -c '
    pg_dump --clean --if-exists --create -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-bangla_library}"
  '
} | awk -v bootstrap="${POSTGRES_USER:-postgres}" '
  $0 == "CREATE ROLE " bootstrap ";" { next }
  index($0, "ALTER ROLE " bootstrap " ") == 1 { next }
  { print }
' | gzip -1
EOF
)")" >"${POSTGRES_DUMP_FILE}"
}

capture_source_redis_dump() {
  log_info "Streaming Redis RDB snapshot."
  run_ssh source "$(compose_remote_script "${SOURCE_REMOTE_APP_DIR}" "$(cat <<'EOF'
compose "${COMPOSE_ARGS[@]}" exec -T redis redis-cli SAVE >/dev/null
compose "${COMPOSE_ARGS[@]}" exec -T redis sh -lc 'cat /data/dump.rdb'
EOF
)")" >"${REDIS_DUMP_FILE}"
}

