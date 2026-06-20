write_target_override_bundle() {
  : >"${TARGET_OVERRIDE_FILE}"
  printf 'BACKEND_PORT=%s\n' "${BACKEND_PORT}" >>"${TARGET_OVERRIDE_FILE}"
  printf 'FRONTEND_PORT=%s\n' "${FRONTEND_PORT}" >>"${TARGET_OVERRIDE_FILE}"
  if [[ -n "${TARGET_PUBLIC_BASE_URL:-}" ]]; then
    printf 'PUBLIC_BASE_URL=%s\n' "${TARGET_PUBLIC_BASE_URL}" >>"${TARGET_OVERRIDE_FILE}"
  fi
  if [[ -n "${TARGET_PUBLIC_API_ORIGIN:-}" ]]; then
    printf 'PUBLIC_API_ORIGIN=%s\n' "${TARGET_PUBLIC_API_ORIGIN}" >>"${TARGET_OVERRIDE_FILE}"
  fi
  if [[ -n "${TARGET_FRONTEND_BASE_URL:-}" ]]; then
    printf 'FRONTEND_BASE_URL=%s\n' "${TARGET_FRONTEND_BASE_URL}" >>"${TARGET_OVERRIDE_FILE}"
  fi
}

require_local_tools() {
  local tools=(bash ssh scp tar gzip python3)
  local tool
  for tool in "${tools[@]}"; do
    command -v "${tool}" >/dev/null 2>&1 || die "Missing required local tool: ${tool}"
  done

  if ! command -v sha256sum >/dev/null 2>&1 && ! command -v shasum >/dev/null 2>&1; then
    die "Missing required local checksum tool: sha256sum or shasum"
  fi

  if [[ -n "${SOURCE_SSH_PASSWORD:-}" || -n "${TARGET_SSH_PASSWORD:-}" ]]; then
    command -v sshpass >/dev/null 2>&1 || die "Password-based SSH requires local sshpass"
  fi
}

resolve_domain_ips() {
  local domain_name="${1:?domain is required}"
  python3 - "${domain_name}" <<'PY'
import socket
import sys

domain = sys.argv[1]
try:
    _name, _aliases, ips = socket.gethostbyname_ex(domain)
except Exception:
    ips = []

for ip in sorted(set(ips)):
    print(ip)
PY
}

preflight_edge_setup() {
  EDGE_SETUP_READY=0
  EDGE_SETUP_REASON="skipped"

  if [[ "${SKIP_EDGE_SETUP}" == "1" ]]; then
    EDGE_SETUP_REASON="disabled"
    return 0
  fi

  if [[ -z "${TARGET_DOMAIN:-}" || -z "${TARGET_CERTBOT_EMAIL:-}" ]]; then
    EDGE_SETUP_REASON="missing_domain_or_certbot_email"
    return 0
  fi

  local resolved_ips
  resolved_ips="$(resolve_domain_ips "${TARGET_DOMAIN}")"
  if [[ -z "${resolved_ips}" ]]; then
    EDGE_SETUP_REASON="dns_unresolved"
    return 0
  fi
  if ! printf '%s\n' "${resolved_ips}" | grep -Fxq "${TARGET_IP}"; then
    EDGE_SETUP_REASON="dns_mismatch"
    log_warn "Skipping edge setup because ${TARGET_DOMAIN} does not resolve to ${TARGET_IP}."
    return 0
  fi

  EDGE_SETUP_READY=1
  EDGE_SETUP_REASON="ready"
}

maybe_prompt_for_cloudflare_change() {
  if [[ -z "${TARGET_DOMAIN:-}" || -z "${TARGET_IP:-}" ]]; then
    return 0
  fi

  local choice
  choice="$(timed_prompt_local "You have to configure the domain ${TARGET_DOMAIN} to point to the target host IP ${TARGET_IP}. Have you done it? [y/N] (auto-continue in 10s): " 10 "n")"
  [[ "${choice}" =~ ^([Yy]|[Yy][Ee][Ss])$ ]]
}

remote_connectivity_check() {
  local role="${1:?role is required}"
  local label endpoint output
  label="$(tr '[:lower:]' '[:upper:]' <<<"${role:0:1}")${role:1}"
  endpoint="$(role_value "${role}" user)@$(role_value "${role}" host):$(role_value "${role}" port)"

  if ! output="$(check_ssh_connection "${role}" 2>&1)"; then
    die "Cannot connect to the ${label} server. Run: ssh-copy-id ${endpoint} from your local machine and retry."
  fi

  log_info "${label} host SSH connection verified: ${endpoint}"
}

remote_os_check() {
  local role="${1:?role is required}"
  local os_id
  os_id="$(remote_run "${role}" "$(cat <<'EOF'
source /etc/os-release
printf '%s\n' "${ID}"
EOF
)")"
  case "${os_id}" in
    ubuntu|debian)
      ;;
    *)
      die "The ${role} server must be running Ubuntu or Debian. Provision a compatible server, update your config with the new host details, and retry."
      ;;
  esac
}

remote_sudo_check() {
  local role="${1:?role is required}"
  if [[ -n "$(role_value "${role}" sudo_password)" ]]; then
    remote_sudo "${role}" "true" >/dev/null
  else
    remote_run "${role}" "sudo -n true" >/dev/null 2>&1 || die "Remote ${role} host requires passwordless sudo or ${role^^}_SUDO_PASSWORD"
  fi
}

source_layout_check() {
  remote_run source "$(app_remote_script "${SOURCE_REMOTE_APP_DIR}" "$(cat <<'EOF'
test -f deploy/compose/docker-compose.yml
test -f deploy/scripts/install-docker.sh
test -f deploy/scripts/setup-host-nginx.sh
test -f automation/lib/common.sh
test -d app/backend/storage
test -f deploy/env/.app.env
EOF
)")" >/dev/null
}

container_status_report_script() {
  cat <<'EOF'
service_status() {
  local service_name="$1"
  local required_health="$2"
  local container_id
  container_id="$(compose "${COMPOSE_ARGS[@]}" ps -q "${service_name}")"
  [[ -n "${container_id}" ]] || {
    echo "missing:${service_name}"
    return 1
  }
  local status health
  status="$(docker inspect -f '{{.State.Status}}' "${container_id}")"
  health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "${container_id}")"
  if [[ "${status}" != "running" ]]; then
    echo "not-running:${service_name}:${status}"
    return 1
  fi
  if [[ "${required_health}" == "1" && -n "${health}" && "${health}" != "healthy" ]]; then
    echo "not-healthy:${service_name}:${health}"
    return 1
  fi
}
EOF
}

source_stack_health_check() {
  local check_script
  check_script="$(cat <<EOF
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
urllib.request.urlopen(f"http://127.0.0.1:{backend_port}/api/csrf/", timeout=15)
urllib.request.urlopen(f"http://127.0.0.1:{frontend_port}/", timeout=15)
print("ok")
PY
EOF
)"
  remote_run source "$(compose_remote_script "${SOURCE_REMOTE_APP_DIR}" "${check_script}")" >/dev/null
}

target_ports_check() {
  local ports_to_check=("${BACKEND_PORT}" "${FRONTEND_PORT}" "80" "443")
  local port_list
  port_list="$(IFS=,; printf '%s' "${ports_to_check[*]}")"
  remote_run target "$(cat <<EOF
python3 - "${port_list}" <<'PY'
import os
import sys

ports = [int(item) for item in sys.argv[1].split(",") if item]
listening = set()
try:
    proc = os.popen("ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null")
    for line in proc:
        parts = line.split()
        if len(parts) >= 4:
            addr = parts[3]
            if ":" in addr:
                listening.add(addr.rsplit(":", 1)[-1])
    proc.close()
except Exception:
    pass

for port in ports:
    if str(port) in listening:
        raise SystemExit(f"port-in-use:{port}")
print("ok")
PY
EOF
)" >/dev/null
}

target_directory_state_check() {
  local state_output
  state_output="$(remote_run target "$(cat <<EOF
app_dir=$(q "${TARGET_REMOTE_APP_DIR}")
bundle_id=$(q "${BUNDLE_ID}")
allow_reset=$(q "${ALLOW_TARGET_RESET}")
python3 - "${TARGET_REMOTE_APP_DIR}" "${BUNDLE_ID}" "${ALLOW_TARGET_RESET}" <<'PY'
import os
import sys

app_dir, bundle_id, allow_reset = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
if not os.path.exists(app_dir):
    print("TARGET_STATE=missing")
    sys.exit(0)
entries = [entry for entry in os.listdir(app_dir) if entry not in (".", "..")]
if not entries:
    print("TARGET_STATE=empty")
    sys.exit(0)
marker_path = os.path.join(app_dir, ".migration-state", "bundle-id")
if os.path.exists(marker_path):
    current = open(marker_path, "r", encoding="utf-8").read().strip()
    if current == bundle_id:
        print("TARGET_STATE=resumable")
        sys.exit(0)
if allow_reset:
    print("TARGET_STATE=resettable")
    sys.exit(0)
print("TARGET_STATE=occupied")
sys.exit(3)
PY
EOF
)")" || true

  if printf '%s\n' "${state_output}" | grep -Fq 'TARGET_STATE=occupied'; then
    die "Target app directory is not empty and is not a recognized resumable restore. Use --allow-target-reset if you intend to wipe it."
  fi

  TARGET_RESET_ALLOWED=0
  if printf '%s\n' "${state_output}" | grep -Eq 'TARGET_STATE=(resumable|resettable)'; then
    TARGET_RESET_ALLOWED=1
  fi
}

