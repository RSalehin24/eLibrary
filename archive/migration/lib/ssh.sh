strict_host_key_options() {
  local mode="${1:-accept-new}"
  case "${mode}" in
    yes)
      printf '%s\n' "-o" "StrictHostKeyChecking=yes"
      ;;
    no)
      printf '%s\n' "-o" "StrictHostKeyChecking=no" "-o" "UserKnownHostsFile=/dev/null"
      ;;
    accept-new|*)
      printf '%s\n' "-o" "StrictHostKeyChecking=accept-new"
      ;;
  esac
}

role_value() {
  local role="${1:?role is required}"
  local field="${2:?field is required}"

  case "${role}:${field}" in
    source:host) printf '%s' "${SOURCE_HOST}" ;;
    source:port) printf '%s' "${SOURCE_PORT}" ;;
    source:user) printf '%s' "${SOURCE_USER}" ;;
    source:key) printf '%s' "${SOURCE_SSH_KEY_PATH:-}" ;;
    source:password) printf '%s' "${SOURCE_SSH_PASSWORD:-}" ;;
    source:sudo_password) printf '%s' "${SOURCE_SUDO_PASSWORD:-}" ;;
    target:host) printf '%s' "${TARGET_IP}" ;;
    target:port) printf '%s' "${TARGET_PORT}" ;;
    target:user) printf '%s' "${TARGET_USER}" ;;
    target:key) printf '%s' "${TARGET_SSH_KEY_PATH:-}" ;;
    target:password) printf '%s' "${TARGET_SSH_PASSWORD:-}" ;;
    target:sudo_password) printf '%s' "${TARGET_SUDO_PASSWORD:-}" ;;
    *)
      return 1
      ;;
  esac
}

run_ssh() {
  local role="${1:?role is required}"
  shift
  local host user port key_path password
  host="$(role_value "${role}" host)"
  user="$(role_value "${role}" user)"
  port="$(role_value "${role}" port)"
  key_path="$(role_value "${role}" key)"
  password="$(role_value "${role}" password)"

  local -a ssh_cmd=(ssh)
  if [[ -n "${port}" ]]; then
    ssh_cmd+=(-p "${port}")
  fi
  if [[ -n "${key_path}" ]]; then
    ssh_cmd+=(-i "${key_path}")
  fi
  while IFS= read -r option; do
    ssh_cmd+=("${option}")
  done < <(strict_host_key_options "${STRICT_HOST_KEY_MODE}")
  ssh_cmd+=("${user}@${host}")
  ssh_cmd+=("$@")

  if [[ -n "${password}" ]]; then
    SSHPASS="${password}" sshpass -e "${ssh_cmd[@]}"
  else
    "${ssh_cmd[@]}"
  fi
}

check_ssh_connection() {
  local role="${1:?role is required}"
  local host user port key_path password
  host="$(role_value "${role}" host)"
  user="$(role_value "${role}" user)"
  port="$(role_value "${role}" port)"
  key_path="$(role_value "${role}" key)"
  password="$(role_value "${role}" password)"

  local -a ssh_cmd=(ssh -o ConnectTimeout=10)
  if [[ -z "${password}" ]]; then
    ssh_cmd+=(-o BatchMode=yes)
  fi
  if [[ -n "${port}" ]]; then
    ssh_cmd+=(-p "${port}")
  fi
  if [[ -n "${key_path}" ]]; then
    ssh_cmd+=(-i "${key_path}")
  fi
  while IFS= read -r option; do
    ssh_cmd+=("${option}")
  done < <(strict_host_key_options "${STRICT_HOST_KEY_MODE}")
  ssh_cmd+=("${user}@${host}" "printf 'connected\n'")

  if [[ -n "${password}" ]]; then
    SSHPASS="${password}" sshpass -e "${ssh_cmd[@]}"
  else
    "${ssh_cmd[@]}"
  fi
}

run_scp_to() {
  local role="${1:?role is required}"
  local local_path="${2:?local path is required}"
  local remote_path="${3:?remote path is required}"
  local host user port key_path password
  host="$(role_value "${role}" host)"
  user="$(role_value "${role}" user)"
  port="$(role_value "${role}" port)"
  key_path="$(role_value "${role}" key)"
  password="$(role_value "${role}" password)"

  local -a scp_cmd=(scp)
  if [[ -n "${port}" ]]; then
    scp_cmd+=(-P "${port}")
  fi
  if [[ -n "${key_path}" ]]; then
    scp_cmd+=(-i "${key_path}")
  fi
  while IFS= read -r option; do
    scp_cmd+=("${option}")
  done < <(strict_host_key_options "${STRICT_HOST_KEY_MODE}")
  scp_cmd+=("${local_path}" "${user}@${host}:${remote_path}")

  if [[ -n "${password}" ]]; then
    SSHPASS="${password}" sshpass -e "${scp_cmd[@]}"
  else
    "${scp_cmd[@]}"
  fi
}

run_scp_from() {
  local role="${1:?role is required}"
  local remote_path="${2:?remote path is required}"
  local local_path="${3:?local path is required}"
  local host user port key_path password
  host="$(role_value "${role}" host)"
  user="$(role_value "${role}" user)"
  port="$(role_value "${role}" port)"
  key_path="$(role_value "${role}" key)"
  password="$(role_value "${role}" password)"

  local -a scp_cmd=(scp)
  if [[ -n "${port}" ]]; then
    scp_cmd+=(-P "${port}")
  fi
  if [[ -n "${key_path}" ]]; then
    scp_cmd+=(-i "${key_path}")
  fi
  while IFS= read -r option; do
    scp_cmd+=("${option}")
  done < <(strict_host_key_options "${STRICT_HOST_KEY_MODE}")
  scp_cmd+=("${user}@${host}:${remote_path}" "${local_path}")

  if [[ -n "${password}" ]]; then
    SSHPASS="${password}" sshpass -e "${scp_cmd[@]}"
  else
    "${scp_cmd[@]}"
  fi
}

remote_run() {
  local role="${1:?role is required}"
  local command_text="${2:?command text is required}"
  run_ssh "${role}" "bash -lc $(printf '%q' "${command_text}")"
}

remote_sudo() {
  local role="${1:?role is required}"
  local command_text="${2:?command text is required}"
  local sudo_password
  sudo_password="$(role_value "${role}" sudo_password)"

  if [[ -n "${sudo_password}" ]]; then
    remote_run "${role}" "printf '%s\n' $(printf '%q' "${sudo_password}") | sudo -S -p '' bash -lc $(printf '%q' "${command_text}")"
  else
    remote_run "${role}" "sudo -n bash -lc $(printf '%q' "${command_text}")"
  fi
}
