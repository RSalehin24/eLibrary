#!/usr/bin/env bash
# Monthly backup (D-33): runs the `backup` one-shot against the running stack and leaves the set in
# a NEW host directory. Encryption and the offsite copy are not done here (tool choice is open).
# Usage: deploy/scripts/backup.sh <new-output-dir>
set -euo pipefail
cd "$(dirname "$0")/../compose"

out="$(realpath -m "${1:?usage: backup.sh <new-output-dir>}")"
[ ! -e "$out" ] || { echo "refusing to overwrite $out" >&2; exit 1; }
mkdir -p "$(dirname "$out")"

# why: run as the invoking user so the host directory is writable and the files belong to them.
docker compose --profile backup run --rm --no-deps \
  --user "$(id -u):$(id -g)" -v "$(dirname "$out"):/backups" \
  backup "/backups/$(basename "$out")"
echo "backup set: $out ($(du -sh "$out" | cut -f1))"
