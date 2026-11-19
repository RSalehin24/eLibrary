#!/usr/bin/env bash
# Monthly backup of every service database (D-33). Writes a NEW directory, never overwrites.
# Encryption and the offsite copy are not done here (tool choice is an open decision).
# Usage: deploy/scripts/backup.sh <new-output-dir>     (COMPOSE_PROJECT_NAME selects the stack)
set -euo pipefail
cd "$(dirname "$0")/../compose"

out="$(realpath -m "${1:?usage: backup.sh <new-output-dir>}")"
[ ! -e "$out" ] || { echo "refusing to overwrite $out" >&2; exit 1; }
databases=(identity catalog reader ingestion notify)
postgres() { docker compose exec -T postgres "$@"; }

# why: exact counts per table, written as "table<TAB>rows", so a restore can be compared.
row_counts() {
  postgres psql -U postgres -d "$1" -tA -F $'\t' -c "
    select table_name, (xpath('/row/c/text()', query_to_xml(
      format('select count(*) as c from %I.%I', table_schema, table_name), false, true, '')))[1]::text
    from information_schema.tables
    where table_schema = 'public' and table_type = 'BASE TABLE' order by 1"
}

mkdir -p "$out"
chmod 700 "$out"
for db in "${databases[@]}"; do
  postgres pg_dump -U postgres -Fc "$db" > "$out/$db.dump"
  row_counts "$db" > "$out/$db.rows"
done
postgres pg_dumpall -U postgres --globals-only > "$out/globals.sql"
chmod 600 "$out"/*   # globals.sql holds role password hashes

{
  echo "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "images=$(docker compose images --format json 2>/dev/null | tr -d '\n' | head -c 4000)"
} > "$out/MANIFEST.txt"
(cd "$out" && sha256sum -- *.dump *.rows globals.sql MANIFEST.txt > MANIFEST.sha256)
echo "backup written to $out ($(du -sh "$out" | cut -f1))"
