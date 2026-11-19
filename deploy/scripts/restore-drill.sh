#!/usr/bin/env bash
# Restore a backup set into an EMPTY, separate Compose project and prove it works (INV-PLT-015).
# Usage: deploy/scripts/restore-drill.sh <backup-dir>
set -euo pipefail
cd "$(dirname "$0")/../compose"

backup="$(realpath "${1:?usage: restore-drill.sh <backup-dir>}")"
project=elibrary-drill
databases=(identity catalog reader ingestion notify)
drill() { docker compose -p "$project" "$@"; }
postgres() { drill exec -T postgres "$@"; }

if [ -n "$(docker compose ps -q 2>/dev/null)" ]; then
  echo "stop the main stack first (the drill needs the same host ports)" >&2; exit 1
fi
(cd "$backup" && sha256sum --check --quiet MANIFEST.sha256)
echo "manifest checksums ok"

start=$(date +%s)
drill down -v --remove-orphans >/dev/null 2>&1
drill up -d --wait postgres >/dev/null 2>&1   # init script creates the roles and empty databases
for db in "${databases[@]}"; do
  # why: --role makes the service role own the restored objects, as after a normal migrate.
  postgres pg_restore -U postgres -d "$db" --role="$db" --no-owner --exit-on-error < "$backup/$db.dump"
  restored="$(postgres psql -U postgres -d "$db" -tA -F $'\t' -c "
    select table_name, (xpath('/row/c/text()', query_to_xml(
      format('select count(*) as c from %I.%I', table_schema, table_name), false, true, '')))[1]::text
    from information_schema.tables
    where table_schema = 'public' and table_type = 'BASE TABLE' order by 1")"
  [ "$restored" = "$(cat "$backup/$db.rows")" ] || { echo "row counts differ in $db" >&2; exit 1; }
done
echo "databases restored, row counts match"
drill up -d --wait >/dev/null 2>&1   # migrate one-shots find the schema current; services must start
echo "stack healthy after restore; drill took $(( $(date +%s) - start )) s"
