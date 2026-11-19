#!/usr/bin/env bash
# Runs INSIDE the `backup` container: dumps every service database into a NEW directory (D-33).
# Usage (via compose): backup-job.sh <new-directory>
set -euo pipefail

out="${1:?usage: backup-job.sh <new-directory>}"
[ ! -e "$out" ] || { echo "refusing to overwrite $out" >&2; exit 1; }
databases=(identity catalog reader ingestion notify)

# why: the password comes from a secret file; a pgpass file in tmpfs keeps it off the command line.
export PGPASSFILE=/tmp/.pgpass PGHOST=postgres PGUSER=postgres
printf 'postgres:5432:*:postgres:%s\n' "$(cat /run/secrets/postgres_password)" > "$PGPASSFILE"
chmod 600 "$PGPASSFILE"

row_counts() {
  psql -d "$1" -tA -F $'\t' -c "
    select table_name, (xpath('/row/c/text()', query_to_xml(
      format('select count(*) as c from %I.%I', table_schema, table_name), false, true, '')))[1]::text
    from information_schema.tables
    where table_schema = 'public' and table_type = 'BASE TABLE' order by 1"
}

mkdir -p "$out"
chmod 700 "$out"
for db in "${databases[@]}"; do
  pg_dump -Fc "$db" > "$out/$db.dump"
  row_counts "$db" > "$out/$db.rows"
done
pg_dumpall --globals-only > "$out/globals.sql"
echo "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$out/MANIFEST.txt"
chmod 600 "$out"/*   # globals.sql holds role password hashes
(cd "$out" && sha256sum -- *.dump *.rows globals.sql MANIFEST.txt > MANIFEST.sha256)
echo "backup written to $out"
