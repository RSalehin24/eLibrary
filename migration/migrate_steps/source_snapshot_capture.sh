capture_source_git_commit() {
  remote_run source "$(app_remote_script "${SOURCE_REMOTE_APP_DIR}" "$(cat <<'EOF'
git rev-parse HEAD 2>/dev/null || true
EOF
)")"
}

capture_db_summary() {
  local role="${1:?role is required}"
  local app_dir="${2:?app dir is required}"
  remote_run "${role}" "$(compose_remote_script "${app_dir}" "$(cat <<'EOF'
table_counts="$(
  cat <<'SQL' | compose "${COMPOSE_ARGS[@]}" exec -T postgres psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-bangla_library}" -At
CREATE OR REPLACE FUNCTION pg_temp.migration_table_counts()
RETURNS TABLE(table_name text, row_count bigint)
LANGUAGE plpgsql
AS $$
DECLARE
  item record;
BEGIN
  FOR item IN
    SELECT schemaname, relname
    FROM pg_stat_user_tables
    ORDER BY schemaname, relname
  LOOP
    RETURN QUERY EXECUTE format(
      'SELECT %L::text, count(*)::bigint FROM %I.%I',
      item.schemaname || '.' || item.relname,
      item.schemaname,
      item.relname
    );
  END LOOP;
END;
$$;
SELECT table_name || '=' || row_count
FROM pg_temp.migration_table_counts()
ORDER BY table_name;
SQL
)"

table_count="$(printf '%s\n' "${table_counts}" | sed '/^$/d' | wc -l | tr -d ' ')"
row_total="$(printf '%s\n' "${table_counts}" | awk -F= 'NF == 2 { total += $2 } END { printf "%.0f\n", total + 0 }')"
row_hash="$(printf '%s\n' "${table_counts}" | sed '/^$/d' | sha256sum | awk '{print $1}')"
role_count="$(
  cat <<'SQL' | compose "${COMPOSE_ARGS[@]}" exec -T postgres psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-bangla_library}" -At
SELECT count(*) FROM pg_roles;
SQL
)"

printf 'DB_TABLE_COUNT=%s\n' "${table_count}"
printf 'DB_ROW_TOTAL=%s\n' "${row_total}"
printf 'DB_ROLE_COUNT=%s\n' "${role_count}"
printf 'DB_TABLE_ROWS_SHA256=%s\n' "${row_hash}"
EOF
)")"
}

capture_redis_summary() {
  local role="${1:?role is required}"
  local app_dir="${2:?app dir is required}"
  remote_run "${role}" "$(compose_remote_script "${app_dir}" "$(cat <<'EOF'
printf 'REDIS_DBSIZE=%s\n' "$(compose "${COMPOSE_ARGS[@]}" exec -T redis redis-cli --raw DBSIZE)"
printf 'REDIS_QUEUE_CELERY=%s\n' "$(compose "${COMPOSE_ARGS[@]}" exec -T redis redis-cli --raw LLEN celery)"
printf 'REDIS_QUEUE_PROCESSING=%s\n' "$(compose "${COMPOSE_ARGS[@]}" exec -T redis redis-cli --raw LLEN processing)"
printf 'REDIS_USED_MEMORY=%s\n' "$(compose "${COMPOSE_ARGS[@]}" exec -T redis redis-cli --raw INFO memory | awk -F: '/^used_memory:/{print $2}' | tr -d '\r')"
EOF
)")"
}

capture_storage_summary() {
  local role="${1:?role is required}"
  local storage_root="${2:?storage root is required}"
  remote_run "${role}" "$(cat <<EOF
python3 - "${storage_root}" <<'PY'
import os
import sys

root = sys.argv[1]
file_count = 0
total_bytes = 0
for base, _dirs, files in os.walk(root):
    for name in files:
        path = os.path.join(base, name)
        try:
            stat = os.stat(path, follow_symlinks=False)
        except FileNotFoundError:
            continue
        file_count += 1
        total_bytes += stat.st_size

print(f"STORAGE_FILE_COUNT={file_count}")
print(f"STORAGE_TOTAL_BYTES={total_bytes}")
PY
EOF
)"
}

write_source_metadata() {
  log_info "Writing source metadata manifest."
  : >"${METADATA_FILE}"
  append_metadata BUNDLE_ID "${BUNDLE_ID}"
  append_metadata SOURCE_HOST "${SOURCE_HOST}"
  append_metadata TARGET_IP "${TARGET_IP}"
  append_metadata EDGE_SETUP_READY "${EDGE_SETUP_READY}"
  append_metadata EDGE_SETUP_REASON "${EDGE_SETUP_REASON}"
  append_metadata SOURCE_GIT_COMMIT "$(capture_source_git_commit)"
  append_metadata SNAPSHOT_COMPLETED_AT "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  append_metadata SOURCE_ENV_SHA256 "$(hash_file "${APP_ENV_BUNDLE_FILE}")"
  append_metadata APP_ARCHIVE_SHA256 "$(hash_file "${APP_ARCHIVE_FILE}")"
  append_metadata STORAGE_ARCHIVE_SHA256 "$(hash_file "${STORAGE_ARCHIVE_FILE}")"
  append_metadata POSTGRES_DUMP_SHA256 "$(hash_file "${POSTGRES_DUMP_FILE}")"
  append_metadata REDIS_DUMP_SHA256 "$(hash_file "${REDIS_DUMP_FILE}")"

  local line
  while IFS= read -r line; do
    [[ -n "${line}" ]] || continue
    append_metadata "SOURCE_${line%%=*}" "${line#*=}"
  done < <(capture_db_summary source "${SOURCE_REMOTE_APP_DIR}")

  while IFS= read -r line; do
    [[ -n "${line}" ]] || continue
    append_metadata "SOURCE_${line%%=*}" "${line#*=}"
  done < <(capture_redis_summary source "${SOURCE_REMOTE_APP_DIR}")

  while IFS= read -r line; do
    [[ -n "${line}" ]] || continue
    append_metadata "SOURCE_${line%%=*}" "${line#*=}"
  done < <(capture_storage_summary source "${SOURCE_REMOTE_APP_DIR}/app/backend/storage")
}

write_bundle_checksums() {
  log_info "Writing bundle checksums."
  write_checksums_manifest \
    "${CHECKSUMS_FILE}" \
    "${APP_ARCHIVE_FILE}" \
    "${STORAGE_ARCHIVE_FILE}" \
    "${POSTGRES_DUMP_FILE}" \
    "${REDIS_DUMP_FILE}" \
    "${APP_ENV_BUNDLE_FILE}" \
    "${TARGET_OVERRIDE_FILE}"
}

run_snapshot() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    log_info "DRY RUN: snapshot would freeze the source and create bundle artifacts under ${BUNDLE_DIR}."
    mark_phase_done snapshot
    return 0
  fi

  freeze_source_stack
  wait_for_source_drain
  stop_source_workers
  capture_source_env
  capture_source_app_archive
  capture_source_storage_archive
  capture_source_postgres_dump
  capture_source_redis_dump
  write_source_metadata
  write_bundle_checksums
  verify_local_checksums "${BUNDLE_DIR}" || die "Local bundle checksum verification failed after snapshot."
  mark_phase_done snapshot
  log_info "Snapshot completed."

  if [[ "${PHASE}" == "snapshot" && "${KEEP_SOURCE_DOWN_ON_SUCCESS}" == "0" ]]; then
    restart_source_stack
  fi
}

verify_bundle_ready_for_restore() {
  local required_files=(
    "${APP_ARCHIVE_FILE}"
    "${STORAGE_ARCHIVE_FILE}"
    "${POSTGRES_DUMP_FILE}"
    "${REDIS_DUMP_FILE}"
    "${APP_ENV_BUNDLE_FILE}"
    "${TARGET_OVERRIDE_FILE}"
    "${METADATA_FILE}"
    "${CHECKSUMS_FILE}"
  )
  local file_path
  for file_path in "${required_files[@]}"; do
    [[ -f "${file_path}" ]] || die "Missing required bundle artifact: ${file_path}"
  done
  verify_local_checksums "${BUNDLE_DIR}" || die "Local bundle checksum verification failed."
  # shellcheck disable=SC1090
  source "${METADATA_FILE}"
}

upload_bundle_to_target() {
  log_info "Uploading bundle to target staging path ${TARGET_REMOTE_BUNDLE_DIR}."
  remote_run target "rm -rf $(q "${TARGET_REMOTE_BUNDLE_DIR}") && mkdir -p $(q "${TARGET_REMOTE_BUNDLE_DIR}")"
  run_scp_to target "${APP_ARCHIVE_FILE}" "${TARGET_REMOTE_BUNDLE_DIR}/app.tar.gz"
  run_scp_to target "${STORAGE_ARCHIVE_FILE}" "${TARGET_REMOTE_BUNDLE_DIR}/storage.tar.gz"
  run_scp_to target "${POSTGRES_DUMP_FILE}" "${TARGET_REMOTE_BUNDLE_DIR}/postgres.sql.gz"
  run_scp_to target "${REDIS_DUMP_FILE}" "${TARGET_REMOTE_BUNDLE_DIR}/redis-dump.rdb"
  run_scp_to target "${APP_ENV_BUNDLE_FILE}" "${TARGET_REMOTE_BUNDLE_DIR}/app.env"
  run_scp_to target "${TARGET_OVERRIDE_FILE}" "${TARGET_REMOTE_BUNDLE_DIR}/target-env-overrides.env"
  run_scp_to target "${METADATA_FILE}" "${TARGET_REMOTE_BUNDLE_DIR}/metadata.env"
  run_scp_to target "${CHECKSUMS_FILE}" "${TARGET_REMOTE_BUNDLE_DIR}/checksums.sha256"
}

verify_remote_bundle_checksums() {
  log_info "Verifying transferred bundle checksums on target."
  remote_run target "cd $(q "${TARGET_REMOTE_BUNDLE_DIR}") && sha256sum -c checksums.sha256 >/dev/null"
}

prepare_target_app_directory() {
  local reset_ok="${ALLOW_TARGET_RESET}"
  if [[ "${TARGET_RESET_ALLOWED}" == "1" ]]; then
    reset_ok="1"
  fi
  log_info "Preparing target application directory ${TARGET_REMOTE_APP_DIR}."
  remote_sudo target "$(cat <<EOF
app_dir=$(q "${TARGET_REMOTE_APP_DIR}")
parent_dir=\$(dirname -- "${TARGET_REMOTE_APP_DIR}")
user_name=$(q "${TARGET_USER}")
reset_ok=$(q "${reset_ok}")
if [[ -d "\${app_dir}" ]]; then
  if [[ "\${reset_ok}" == "1" ]]; then
    rm -rf "\${app_dir}"
  else
    if find "\${app_dir}" -mindepth 1 -maxdepth 1 | grep -q .; then
      echo "Target app dir is not empty and reset is not allowed." >&2
      exit 1
    fi
  fi
fi
mkdir -p "\${parent_dir}" "\${app_dir}"
chown -R "\${user_name}:\${user_name}" "\${app_dir}"
EOF
)"
}

extract_target_app_bundle() {
  log_info "Extracting application snapshot on target."
  remote_run target "$(cat <<EOF
mkdir -p $(q "${TARGET_REMOTE_APP_DIR}")
tar -xzf $(q "${TARGET_REMOTE_BUNDLE_DIR}/app.tar.gz") -C $(q "${TARGET_REMOTE_APP_DIR}")
mkdir -p $(q "${TARGET_REMOTE_APP_DIR}/.migration-state")
printf '%s\n' $(q "${BUNDLE_ID}") > $(q "${TARGET_REMOTE_APP_DIR}/.migration-state/bundle-id")
cp $(q "${TARGET_REMOTE_BUNDLE_DIR}/app.env") $(q "${TARGET_REMOTE_APP_DIR}/deploy/env/.app.env")
if [[ -s $(q "${TARGET_REMOTE_BUNDLE_DIR}/target-env-overrides.env") ]]; then
  cd $(q "${TARGET_REMOTE_APP_DIR}")
  python3 automation/lib/env_tools.py merge deploy/env/.app.env $(q "${TARGET_REMOTE_BUNDLE_DIR}/target-env-overrides.env") deploy/env/.app.env.merged --non-empty-only
  mv deploy/env/.app.env.merged deploy/env/.app.env
fi
EOF
)"
}

