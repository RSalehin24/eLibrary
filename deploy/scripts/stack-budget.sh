#!/usr/bin/env bash
# Spike S-06: cold start, idle and loaded memory, single-service restart of the Compose stack.
# Usage: deploy/scripts/stack-budget.sh   (images must already be built)
set -euo pipefail
cd "$(dirname "$0")/../compose"

now() { date +%s.%N; }
elapsed() { awk -v a="$1" -v b="$2" 'BEGIN { printf "%.1f", b - a }'; }
memory_mib() {
  docker stats --no-stream --format '{{.MemUsage}}' | awk '{
    value = $1; unit = value; sub(/^[0-9.]+/, "", unit); sub(/[A-Za-z]+$/, "", value)
    if (unit == "GiB") value *= 1024; else if (unit == "KiB") value /= 1024; else if (unit == "B") value /= 1048576
    total += value
  } END { printf "%.0f", total }'
}

docker compose down --remove-orphans >/dev/null 2>&1
start=$(now)
docker compose up -d --wait >/dev/null 2>&1
echo "cold start to all healthy: $(elapsed "$start" "$(now)") s"
sleep 10
echo "idle memory (all containers): $(memory_mib) MiB"

# Load: 400 requests, 20 in parallel, through Caddy to the gateway (404 is fine; it is the path that counts).
seq 400 | xargs -P 20 -I{} curl -sk -o /dev/null https://localhost:8443/api/identity/x
echo "loaded memory right after 400 requests: $(memory_mib) MiB"

start=$(now)
docker compose restart identity >/dev/null 2>&1
until [ "$(docker compose ps identity --format '{{.Health}}')" = "healthy" ]; do sleep 0.5; done
echo "single service restart to healthy: $(elapsed "$start" "$(now)") s"
docker compose down >/dev/null 2>&1
