#!/bin/bash
set -euo pipefail

PROFILE="colima"

show_help() {
  cat <<EOF
dockerctl - Manage Docker with Colima on macOS

Usage:
  dockerctl [command]

Commands:
  start          Start Colima and wait for Docker
  stop           Stop Colima
  restart        Restart Colima
  reset          Reset broken Colima instance
  status         Show Colima and Docker status
  help, -h, --help
                 Show this help message

Default:
  If no command is given, "start" is used.

Behavior:
  - On macOS:
      * installs Homebrew if missing
      * installs Colima if missing
      * installs Docker CLI if missing
      * installs Docker Compose if missing
      * installs Docker Buildx if missing
  - On non-macOS:
      * does not install Colima
      * asks you to install Docker or Docker Compose manually if missing
EOF
}

is_macos() {
  [ "$(uname -s)" = "Darwin" ]
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

have_docker_compose() {
  docker compose version >/dev/null 2>&1 || return 1
  return 0
}

have_any_compose() {
  have_docker_compose || have_cmd docker-compose
}

have_docker_buildx() {
  docker buildx version >/dev/null 2>&1 || return 1
  return 0
}

install_homebrew() {
  if have_cmd brew; then
    return 0
  fi

  echo "Homebrew not found. Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
}

ensure_docker_cli_plugin_dirs() {
  local plugin_dir=""
  local config_file="${HOME}/.docker/config.json"

  if [[ -d "/opt/homebrew/lib/docker/cli-plugins" ]]; then
    plugin_dir="/opt/homebrew/lib/docker/cli-plugins"
  elif [[ -d "/usr/local/lib/docker/cli-plugins" ]]; then
    plugin_dir="/usr/local/lib/docker/cli-plugins"
  else
    return 0
  fi

  mkdir -p "${HOME}/.docker"

  python3 - "${config_file}" "${plugin_dir}" <<'PY'
import json
import os
import sys

cfg_path = sys.argv[1]
plugin_dir = sys.argv[2]

data = {}
if os.path.exists(cfg_path):
  try:
    with open(cfg_path, "r", encoding="utf-8") as fh:
      data = json.load(fh)
  except Exception as exc:
    print(f"[WARN] Skipping Docker CLI plugin config update: {exc}", file=sys.stderr)
    sys.exit(0)

dirs = data.get("cliPluginsExtraDirs")
if isinstance(dirs, list):
    if plugin_dir not in dirs:
        dirs.append(plugin_dir)
elif isinstance(dirs, str):
    dirs = [dirs] if dirs == plugin_dir else [dirs, plugin_dir]
else:
    dirs = [plugin_dir]

data["cliPluginsExtraDirs"] = dirs

with open(cfg_path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2)
    fh.write("\n")
PY
}

ensure_compose() {
  ensure_docker_cli_plugin_dirs

  if have_any_compose; then
    return 0
  fi

  echo "Docker Compose not found. Installing Docker Compose..."
  brew install docker-compose

  ensure_docker_cli_plugin_dirs

  if have_any_compose; then
    return 0
  fi

  echo "Docker Compose install completed but command is still unavailable."
  echo "If needed, open a new shell and retry."
  exit 1
}

ensure_buildx() {
  ensure_docker_cli_plugin_dirs

  if have_docker_buildx; then
    return 0
  fi

  echo "Docker Buildx not found. Installing Docker Buildx..."
  brew install docker-buildx

  ensure_docker_cli_plugin_dirs

  if have_docker_buildx; then
    return 0
  fi

  echo "Docker Buildx install completed but command is still unavailable in this shell."
  echo "Continuing with classic builder; open a new shell later if you want buildx enabled."
  return 0
}

ensure_macos_tools() {
  if ! is_macos; then
    if ! have_cmd docker; then
      echo "Docker is not installed."
      echo "Please install Docker for your operating system."
      exit 1
    fi

    if ! have_any_compose; then
      echo "Docker Compose is not installed."
      echo "Please install Docker Compose for your operating system."
      exit 1
    fi

    return 0
  fi

  install_homebrew

  if ! have_cmd colima; then
    echo "Colima not found. Installing Colima..."
    brew install colima
  fi

  if ! have_cmd docker; then
    echo "Docker CLI not found. Installing Docker CLI..."
    brew install docker
  fi

  ensure_compose
  ensure_buildx
}

start_colima() {
  echo "Starting Colima..."

  if colima start --runtime docker; then
    return 0
  fi

  echo "Start failed. Attempting recovery..."

  colima stop -f || true
  colima delete -f || true
  rm -rf "$HOME/.lima/colima"
  rm -rf "$HOME/.colima/_templates/colima.yaml" "$HOME/.colima/colima.yaml"

  echo "Recreating Colima..."
  colima start --runtime docker
}

