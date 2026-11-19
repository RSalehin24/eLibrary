#!/usr/bin/env bash
# Spike S-09: seed sentinel rows, back up, restore into a fresh project, verify the sentinels.
set -euo pipefail
cd "$(dirname "$0")/../compose"

target="$(mktemp -d)/set"
docker compose up -d --wait >/dev/null 2>&1
for db in identity catalog; do
  docker compose exec -T postgres psql -U postgres -d "$db" -q -c "
    create table if not exists drill_sentinel (note text);
    alter table drill_sentinel owner to $db;
    insert into drill_sentinel values ('from $db before backup');"
done
begin=$(date +%s)
../scripts/backup.sh "$target"
echo "backup took $(( $(date +%s) - begin )) s"
docker compose down >/dev/null 2>&1
../scripts/restore-drill.sh "$target"
for db in identity catalog; do
  note="$(docker compose -p elibrary-drill exec -T postgres psql -U "$db" -d "$db" -tA -c 'select note from drill_sentinel')"
  [ "$note" = "from $db before backup" ] || { echo "sentinel missing in $db" >&2; exit 1; }
done
echo "sentinel rows survived the restore, read as the service roles"
docker compose -p elibrary-drill down -v >/dev/null 2>&1
rm -rf "$(dirname "$target")"
