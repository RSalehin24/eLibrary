hash_file() {
  local path="${1:?path is required}"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${path}" | awk '{print $1}'
    return 0
  fi

  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "${path}" | awk '{print $1}'
    return 0
  fi

  return 1
}

write_checksums_manifest() {
  local manifest_path="${1:?manifest path is required}"
  shift
  : >"${manifest_path}"
  local file_path base_name hash_value
  for file_path in "$@"; do
    base_name="$(basename -- "${file_path}")"
    hash_value="$(hash_file "${file_path}")" || return 1
    printf '%s  %s\n' "${hash_value}" "${base_name}" >>"${manifest_path}"
  done
}

verify_local_checksums() {
  local bundle_dir="${1:?bundle dir is required}"
  local manifest_path="${bundle_dir}/checksums.sha256"

  if command -v sha256sum >/dev/null 2>&1; then
    (cd "${bundle_dir}" && sha256sum -c "${manifest_path##*/}" >/dev/null)
    return 0
  fi

  if command -v shasum >/dev/null 2>&1; then
    (cd "${bundle_dir}" && shasum -a 256 -c "${manifest_path##*/}" >/dev/null)
    return 0
  fi

  return 1
}

append_metadata() {
  local key="${1:?key is required}"
  local value="${2-}"
  printf '%s=%s\n' "${key}" "${value}" >>"${METADATA_FILE}"
}

free_kb_for_path() {
  local path="${1:?path is required}"
  df -Pk "${path}" | awk 'NR==2 {print $4}'
}

