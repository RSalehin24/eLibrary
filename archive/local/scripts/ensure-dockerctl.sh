#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
TARGET="/usr/local/bin/dockerctl"
SOURCE="${SCRIPT_DIR}/dockerctl"

if [ ! -f "$SOURCE" ]; then
  echo "Error: source dockerctl not found at $SOURCE"
  exit 1
fi

if [ ! -x "$SOURCE" ]; then
  chmod +x "$SOURCE"
fi

needs_install=true
if [ -L "$TARGET" ]; then
  current_target="$(readlink "$TARGET" || true)"
  if [ "$current_target" = "$SOURCE" ]; then
    needs_install=false
  fi
fi

if [ "$needs_install" = true ]; then
  echo "Installing/updating dockerctl..."
  sudo mkdir -p "$(dirname "$TARGET")"
  sudo ln -sfn "$SOURCE" "$TARGET"
  echo "dockerctl is ready at $TARGET"
fi
