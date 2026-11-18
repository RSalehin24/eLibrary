app_remote_script() {
  local app_dir="${1:?app dir is required}"
  local body="${2:?body is required}"
  cat <<EOF
set -euo pipefail
cd $(printf '%q' "${app_dir}")
${body}
EOF
}

compose_remote_script() {
  local app_dir="${1:?app dir is required}"
  local body="${2:?body is required}"
  cat <<EOF
set -euo pipefail
cd $(printf '%q' "${app_dir}")
source automation/lib/common.sh
load_env_if_present deploy/env/.app.env
COMPOSE_ARGS=(-f deploy/compose/docker-compose.yml)
${body}
EOF
}

