#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  sudo bash deploy/scripts/install-nginx.sh [required_version]

Examples:
  sudo bash deploy/scripts/install-nginx.sh
  sudo bash deploy/scripts/install-nginx.sh 1.29.4

Installs or upgrades Nginx from nginx.org packages on an Ubuntu-style host. When
a version is provided, the script resolves the matching apt package version.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root (use sudo)." >&2
  exit 1
fi

required_version="${1:-}"

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y curl gnupg2 ca-certificates ubuntu-keyring lsb-release

install -m 0755 -d /etc/apt/keyrings
if [[ ! -f /etc/apt/keyrings/nginx.asc ]]; then
  curl -fsSL https://nginx.org/keys/nginx_signing.key -o /etc/apt/keyrings/nginx.asc
  chmod a+r /etc/apt/keyrings/nginx.asc
fi

. /etc/os-release
cat >/etc/apt/sources.list.d/nginx.list <<EOF
deb [signed-by=/etc/apt/keyrings/nginx.asc] http://nginx.org/packages/ubuntu ${VERSION_CODENAME} nginx
deb-src [signed-by=/etc/apt/keyrings/nginx.asc] http://nginx.org/packages/ubuntu ${VERSION_CODENAME} nginx
EOF

apt-get update

resolve_package_version() {
  local package_name="${1:?package name is required}"
  local short_version="${2:-}"

  if [[ -z "${short_version}" ]]; then
    apt-cache madison "${package_name}" | awk 'NR==1 { print $3 }'
    return
  fi

  apt-cache madison "${package_name}" | awk -v requested="${short_version}" '
    index($3, requested) > 0 { print $3; exit }
  '
}

nginx_package_version="$(resolve_package_version nginx "${required_version}")"
if [[ -z "${nginx_package_version}" ]]; then
  echo "Unable to resolve nginx version for ${required_version:-latest}." >&2
  exit 1
fi

apt-get install -y "nginx=${nginx_package_version}"
apt-mark hold nginx
systemctl enable nginx
systemctl restart nginx
nginx -v
