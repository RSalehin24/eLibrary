ensure_config_file() {
  local example_file="${1:?example file is required}"
  local target_file="${2:?target file is required}"

  if [[ -f "${target_file}" ]]; then
    return 0
  fi

  mkdir -p "$(dirname -- "${target_file}")"
  cp "${example_file}" "${target_file}"
  die "Prepared ${target_file}. Fill in the real values and rerun the migration command."
}

load_config_file() {
  local env_file="${1:?env file is required}"
  eval "$(
    python3 "${REPO_ROOT}/automation/lib/env_tools.py" shell-export "${env_file}"
  )"
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

is_true() {
  case "${1:-0}" in
    1|true|TRUE|yes|YES|on|ON)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

normalize_bool_var() {
  local var_name="${1:?var name is required}"
  local default_value="${2:-0}"
  local current_value="${!var_name:-}"
  if [[ -z "${current_value}" ]]; then
    printf -v "${var_name}" '%s' "${default_value}"
    return 0
  fi
  if is_true "${current_value}"; then
    printf -v "${var_name}" '1'
  else
    printf -v "${var_name}" '0'
  fi
}

default_if_empty() {
  local var_name="${1:?var name is required}"
  local default_value="${2:-}"
  if [[ -z "${!var_name:-}" ]]; then
    printf -v "${var_name}" '%s' "${default_value}"
  fi
}

phase_marker_path() {
  local phase_name="${1:?phase name is required}"
  printf '%s/.phase-%s.done\n' "${BUNDLE_DIR}" "${phase_name}"
}

phase_is_done() {
  local phase_name="${1:?phase name is required}"
  [[ -f "$(phase_marker_path "${phase_name}")" ]]
}

mark_phase_done() {
  local phase_name="${1:?phase name is required}"
  : >"$(phase_marker_path "${phase_name}")"
}

latest_bundle_id() {
  local base_dir="${1:?base dir is required}"
  find "${base_dir}" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | sort | tail -n 1 | xargs -I{} basename "{}"
}

timed_prompt_local() {
  local prompt_text="${1:?prompt text is required}"
  local timeout_seconds="${2:-5}"
  local default_value="${3:-}"
  local response=""

  if [[ ! -t 0 ]]; then
    printf '%s' "${default_value}"
    return 0
  fi

  printf '%s' "${prompt_text}"
  if IFS= read -r -t "${timeout_seconds}" response; then
    printf '\n'
  else
    printf '\n'
    response="${default_value}"
  fi

  if [[ -z "${response}" ]]; then
    response="${default_value}"
  fi

  printf '%s' "${response}"
}
