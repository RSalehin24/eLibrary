log_timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log_line() {
  local level="${1:?level is required}"
  shift
  local line
  line="[${level}] $*"
  printf '[%s] %s\n' "$(log_timestamp)" "${line}"
  if [[ -n "${LOG_FILE:-}" ]]; then
    printf '[%s] %s\n' "$(log_timestamp)" "${line}" >>"${LOG_FILE}"
  fi
}

log_info() {
  log_line INFO "$@"
}

log_warn() {
  log_line WARN "$@"
}

log_error() {
  local ts
  ts="$(log_timestamp)"
  printf '[%s] [ERROR] %s\n' "${ts}" "$*" >&2
  if [[ -n "${LOG_FILE:-}" ]]; then
    printf '[%s] [ERROR] %s\n' "${ts}" "$*" >>"${LOG_FILE}"
  fi
}

die() {
  log_error "$@"
  exit 1
}

run_local_cmd() {
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    log_info "DRY RUN: $*"
    return 0
  fi
  "$@"
}
