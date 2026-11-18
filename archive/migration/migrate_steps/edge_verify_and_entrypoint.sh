maybe_configure_target_edge() {
  preflight_edge_setup

  if [[ "${EDGE_SETUP_READY}" != "1" ]]; then
    append_metadata EDGE_SETUP_STATUS "skipped:${EDGE_SETUP_REASON}"
    log_info "Skipping edge setup: ${EDGE_SETUP_REASON}."
    if [[ "${EDGE_SETUP_REASON}" == "dns_mismatch" ]]; then
      log_info "After Cloudflare points ${TARGET_DOMAIN} to ${TARGET_IP}, rerun --phase verify --resume to finish nginx/certbot setup."
    fi
    return 0
  fi

  log_info "Configuring target nginx/certbot edge."
  remote_sudo target "cd $(q "${TARGET_REMOTE_APP_DIR}") && bash deploy/scripts/setup-host-nginx.sh $(q "${TARGET_DOMAIN}") $(q "${TARGET_CERTBOT_EMAIL}") $(q "${TARGET_REMOTE_APP_DIR}") $(q "${BACKEND_PORT}") $(q "${FRONTEND_PORT}") $(q "${DEPLOY_NGINX_CONFIG_NAME}") $(q "${DEPLOY_NGINX_CONF_DIR}") $(q "${DEPLOY_NGINX_VERSION}")"
  remote_run target "$(cat <<EOF
python3 - "${TARGET_DOMAIN}" <<'PY'
import sys
import urllib.request

domain = sys.argv[1]
urllib.request.urlopen(f"https://{domain}/", timeout=20)
urllib.request.urlopen(f"https://{domain}/api/csrf/", timeout=20)
print("ok")
PY
EOF
)" >/dev/null
  append_metadata EDGE_SETUP_STATUS "configured"
}

run_verify() {
  verify_bundle_ready_for_restore

  if [[ "${TARGET_PRESTART_SUMMARY_MATCH:-0}" != "1" ]]; then
    die "Data verification failed — the restore may be incomplete. Review the migration log at ${LOG_FILE}, fix the issue on the target server, and retry with --phase restore --resume."
  fi

  if [[ "${DRY_RUN}" == "1" ]]; then
    log_info "DRY RUN: verify would check target service health and optional edge setup."
    mark_phase_done verify
    return 0
  fi

  target_service_health_check
  verify_target_live_summaries
  maybe_configure_target_edge
  append_metadata VERIFIED_AT "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mark_phase_done verify
  log_info "Verification completed."
}

phase_should_run() {
  local phase_name="${1:?phase name is required}"
  if [[ "${RESUME}" == "1" && "$(phase_is_done "${phase_name}" && echo yes || echo no)" == "yes" ]]; then
    log_info "Skipping ${phase_name}; already marked complete in ${BUNDLE_DIR}."
    return 1
  fi
  return 0
}

cleanup_remote_bundle_on_success() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    return 0
  fi
  remote_run target "rm -rf $(q "${TARGET_REMOTE_BUNDLE_DIR}")" >/dev/null 2>&1 || true
}

finalize_success() {
  FINAL_SUCCESS=1
  if [[ "${SOURCE_FROZEN}" == "1" && "${KEEP_SOURCE_DOWN_ON_SUCCESS}" == "0" ]]; then
    restart_source_stack
  fi

  cleanup_remote_bundle_on_success

  if [[ "${KEEP_STAGING}" == "0" && "${DRY_RUN}" == "0" ]]; then
    rm -rf "${BUNDLE_DIR}"
    log_info "Removed local staging bundle ${BUNDLE_DIR}."
  fi
}

on_exit() {
  local exit_code=$?
  if [[ "${exit_code}" != "0" && "${SOURCE_FROZEN}" == "1" ]]; then
    log_warn "Failure detected after source freeze; attempting to restart the source services."
    restart_source_stack || true
  fi
  exit "${exit_code}"
}

main() {
  parse_args "$@"
  initialize_config
  validate_required_config
  trap on_exit EXIT

  if [[ "${PHASE}" == "preflight" || "${PHASE}" == "full" ]]; then
    phase_should_run preflight && run_preflight
  fi

  if [[ "${PHASE}" == "snapshot" || "${PHASE}" == "full" ]]; then
    if ! phase_is_done preflight; then
      log_info "Snapshot requires preflight first."
      run_preflight
    fi
    phase_should_run snapshot && run_snapshot
  fi

  if [[ "${PHASE}" == "restore" || "${PHASE}" == "full" ]]; then
    phase_should_run restore && run_restore
  fi

  if [[ "${PHASE}" == "verify" || "${PHASE}" == "full" ]]; then
    phase_should_run verify && run_verify
  fi

  finalize_success
}

main "$@"
