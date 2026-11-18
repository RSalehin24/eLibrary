#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "This file is meant to be sourced, not executed directly." >&2
  exit 1
fi

set -euo pipefail

repo_root_from() {
  local source_path="${1:?source path is required}"
  local search_dir
  search_dir="$(cd -- "$(dirname -- "${source_path}")" >/dev/null 2>&1 && pwd)"

  while [[ "${search_dir}" != "/" ]]; do
    if [[ -d "${search_dir}/.git" || -f "${search_dir}/AGENTS.md" ]]; then
      printf '%s\n' "${search_dir}"
      return 0
    fi
    search_dir="$(dirname -- "${search_dir}")"
  done

  return 1
}

print_info() {
  printf '[INFO] %s\n' "$*"
}

print_warn() {
  printf '[WARN] %s\n' "$*" >&2
}

print_error() {
  printf '[ERROR] %s\n' "$*" >&2
}

die() {
  print_error "$@"
  exit 1
}

require_cmd() {
  local command_name="${1:?command name is required}"
  command -v "${command_name}" >/dev/null 2>&1 || die "Missing required command: ${command_name}"
}

load_env_if_present() {
  local env_file="${1:?env file is required}"
  local automation_lib_dir
  automation_lib_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
  if [[ -f "${env_file}" ]]; then
    require_cmd python3
    eval "$(
      python3 "${automation_lib_dir}/env_tools.py" shell-export "${env_file}"
    )"
  fi
}

read_env_value_from_file() {
  local env_file="${1:?env file is required}"
  local key_name="${2:?env key is required}"
  local value=""

  if [[ -f "${env_file}" ]]; then
    value="$(grep "^${key_name}=" "${env_file}" | tail -n 1 | cut -d '=' -f2- || true)"
  fi

  printf '%s' "${value}"
}

effective_env_value() {
  local key_name="${1:?env key is required}"
  local default_value="${2:-}"
  local current_value="${!key_name:-}"

  if [[ -n "${current_value}" ]]; then
    printf '%s' "${current_value}"
    return 0
  fi

  printf '%s' "${default_value}"
}

print_super_admin_credentials() {
  local email="${1:?email is required}"
  local password="${2:?password is required}"
  local heading="${3:-Super admin credentials}"
  local note="${4:-}"

  cat <<EOF
${heading}
Email: ${email}
Password: ${password}
EOF

  if [[ -n "${note}" ]]; then
    printf '%s\n' "${note}"
  fi
}

ensure_env_file() {
  local template_file="${1:?template file is required}"
  local target_file="${2:?target file is required}"
  local automation_lib_dir
  automation_lib_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

  require_cmd python3
  mkdir -p "$(dirname -- "${target_file}")"
  python3 "${automation_lib_dir}/env_tools.py" scaffold "${template_file}" "${target_file}"
}

resolve_compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    printf 'docker compose'
    return 0
  fi

  if command -v docker-compose >/dev/null 2>&1; then
    printf 'docker-compose'
    return 0
  fi

  return 1
}

compose() {
  local compose_cmd
  compose_cmd="$(resolve_compose_cmd)" || die "Docker Compose is not available."
  if [[ "${compose_cmd}" == "docker compose" ]]; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

prepare_log_file() {
  local log_file="${1:?log file is required}"
  mkdir -p "$(dirname -- "${log_file}")"
  touch "${log_file}"
}

timed_prompt() {
  local prompt_text="${1:?prompt text is required}"
  local timeout_seconds="${2:-5}"
  local default_value="${3:-}"
  local response=""
  local prompt_in="/dev/stdin"
  local prompt_out="/dev/stderr"
  local remaining

  if [[ "${NON_INTERACTIVE:-}" == "1" || "${NON_INTERACTIVE:-}" == "yes" ]]; then
    printf '%s' "${default_value}"
    return 0
  fi

  if [[ -r /dev/tty && -w /dev/tty ]]; then
    prompt_in="/dev/tty"
    prompt_out="/dev/tty"
  elif [[ ! -t 0 ]]; then
    printf '%s' "${default_value}"
    return 0
  fi

  if [[ ! "${timeout_seconds}" =~ ^[0-9]+$ ]]; then
    timeout_seconds=5
  fi

  remaining="${timeout_seconds}"
  while (( remaining > 0 )); do
    printf '\r%s (auto-default in %ss): ' "${prompt_text}" "${remaining}" >"${prompt_out}"
    if IFS= read -r -t 1 response <"${prompt_in}"; then
      break
    fi
    ((remaining--))
  done

  if [[ -z "${response}" ]]; then
    response="${default_value}"
  fi

  printf '\n' >"${prompt_out}"
  printf '%s' "${response}"
}

timed_yes_no_prompt() {
  local prompt_text="${1:?prompt text is required}"
  local timeout_seconds="${2:-5}"
  local default_value="${3:-n}"
  local response=""
  local prompt_in="/dev/stdin"
  local prompt_out="/dev/stderr"
  local remaining

  case "${default_value}" in
    y|Y)
      default_value="y"
      ;;
    *)
      default_value="n"
      ;;
  esac

  if [[ "${NON_INTERACTIVE:-}" == "1" || "${NON_INTERACTIVE:-}" == "yes" ]]; then
    printf '%s' "${default_value}"
    return 0
  fi

  if [[ -r /dev/tty && -w /dev/tty ]]; then
    prompt_in="/dev/tty"
    prompt_out="/dev/tty"
  elif [[ ! -t 0 ]]; then
    printf '%s' "${default_value}"
    return 0
  fi

  if [[ ! "${timeout_seconds}" =~ ^[0-9]+$ ]]; then
    timeout_seconds=5
  fi

  remaining="${timeout_seconds}"
  while (( remaining > 0 )); do
    printf '\r%s yes[y]/no[n] (default %s in %ss): ' "${prompt_text}" "${default_value}" "${remaining}" >"${prompt_out}"
    if IFS= read -r -n 1 -t 1 response <"${prompt_in}"; then
      case "${response}" in
        y|Y)
          response="y"
          break
          ;;
        n|N)
          response="n"
          break
          ;;
        *)
          response=""
          ;;
      esac
    fi
    ((remaining--))
  done

  if [[ -z "${response}" ]]; then
    response="${default_value}"
  fi

  printf '\n' >"${prompt_out}"
  printf '%s' "${response}"
}

service_group_for_logs() {
  local service_name="${1:?service name is required}"

  case "${service_name}" in
    frontend)
      printf 'frontend'
      ;;
    backend)
      printf 'backend worker processing-worker beat'
      ;;
    *)
      return 1
      ;;
  esac
}
