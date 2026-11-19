#!/usr/bin/env bash
# Gate Q8: model-check every formal model with TLC and Alloy; fail on any counterexample or error.
# Needs the jars under tools/ (not in git); checksums are pinned below.
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
models="$root/planning/03-correctness/formal-models"
tla_jar="$root/tools/tlaplus-1.7.4/tla2tools.jar"
alloy_jar="$root/tools/alloy-6.2.0/org.alloytools.alloy.dist.jar"
export PATH="$PATH:/usr/lib/jvm/default/bin"

# why: the jars are downloaded without a published checksum, so pin what was reviewed (D-69).
echo "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88  $tla_jar" | sha256sum --check --quiet
echo "6b8c1cb5bc93bedfc7c61435c4e1ab6e688a242dc702a394628d9a9801edb78d  $alloy_jar" | sha256sum --check --quiet

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

tlc() {   # tlc <config-name> <module-name>
  (cd "$models/tla" && timeout 280 java -Xmx2g -XX:+UseParallelGC -cp "$tla_jar" tlc2.TLC \
      -config "$1.cfg" -workers 4 -deadlock -metadir "$work/$1" "$2.tla") > "$work/$1.out" 2>&1 || true
  grep -q "No error has been found" "$work/$1.out" || { cat "$work/$1.out"; echo "FAIL TLC $1" >&2; exit 1; }
  echo "ok   TLC $1: $(grep -E 'distinct states found' "$work/$1.out" | tail -1 | sed 's/.*generated, //')"
}
tlc Outbox Outbox
tlc OutboxReset Outbox
tlc ReadOnce ReadOnce
tlc MCJobLifecycle MCJobLifecycle

(cd "$models/alloy" && timeout 280 java -jar "$alloy_jar" exec -f -o "$work/alloy" access.als) > "$work/alloy.out" 2>&1 || true
# A `check` that is SAT found a counterexample; UNSAT means none within scope.
if awk '/ check / && $NF == "SAT" { bad = 1; print } END { exit !bad }' "$work/alloy.out"; then
  echo "FAIL Alloy counterexample" >&2; exit 1
fi
[ "$(grep -c ' check .* UNSAT' "$work/alloy.out")" -ge 8 ] || { cat "$work/alloy.out"; echo "FAIL Alloy did not run" >&2; exit 1; }
echo "ok   Alloy access: $(grep -c ' check .* UNSAT' "$work/alloy.out") assertions hold"
