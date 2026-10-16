#!/usr/bin/env bash

docker_repository_distribution() {
  local release_file="${1:?OS release file is required}"
  local ID="" VERSION_CODENAME=""
  # The host's standard OS release file supplies trusted distribution metadata.
  source "${release_file}"
  case "${ID}" in
    ubuntu|debian) ;;
    *) echo "Docker installation requires Ubuntu or Debian." >&2; return 1 ;;
  esac
  if [[ ! "${VERSION_CODENAME}" =~ ^[a-z][a-z0-9]*$ ]]; then
    echo "The OS release file must contain a valid distribution codename." >&2
    return 1
  fi
  printf '%s %s\n' "${ID}" "${VERSION_CODENAME}"
}
