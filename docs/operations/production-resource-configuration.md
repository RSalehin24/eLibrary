# Production Resource Configuration

This document explains every CPU and memory knob available in the deployment,
how to pick values for your server, and the trade-offs to expect.

---

## Architecture overview

```
Host OS (Ubuntu / Debian)
└── Docker Compose (deploy/compose/docker-compose.yml)
    ├── postgres       — relational database
    ├── redis          — Celery broker + result backend
    ├── backend        — Gunicorn / Django HTTP
    ├── worker         — Celery general queue (email, catalog tasks)
    ├── processing-worker — Celery book-scraping queue (CPU/RAM heavy)
    ├── beat           — Celery periodic scheduler
    └── frontend       — Nginx static file server
```

All resource limits live in `deploy/env/app.env` (copy of
`deploy/env/app.env.example`). Docker Compose reads them at
`docker compose up` time. **You never need to edit the YAML directly.**

---

## Quick reference — all resource variables

| Variable                        | Default | Container         | What it controls                  |
| ------------------------------- | ------- | ----------------- | --------------------------------- |
| `BACKEND_MEM_LIMIT`             | `700m`  | backend           | Max RAM for Gunicorn processes    |
| `BACKEND_CPU_LIMIT`             | `1.0`   | backend           | CPU cores (fractional allowed)    |
| `WORKER_MEM_LIMIT`              | `600m`  | worker            | Max RAM for general Celery worker |
| `WORKER_CPU_LIMIT`              | `0.5`   | worker            | CPU cores                         |
| `PROCESSING_WORKER_MEM_LIMIT`   | `900m`  | processing-worker | Max RAM for book-scraping worker  |
| `PROCESSING_WORKER_CPU_LIMIT`   | `2.0`   | processing-worker | CPU cores                         |
| `REDIS_MEM_LIMIT`               | `320m`  | redis             | Hard container memory cap         |
| `REDIS_CPU_LIMIT`               | `0.5`   | redis             | CPU cores                         |
| `REDIS_MAXMEMORY`               | `256mb` | redis             | Redis in-process eviction limit   |
| `GUNICORN_WORKERS`              | `2`     | backend           | Parallel HTTP worker processes    |
| `GUNICORN_TIMEOUT`              | `120`   | backend           | Request timeout (seconds)         |
| `GUNICORN_MAX_REQUESTS`         | `500`   | backend           | Requests before worker recycles   |
| `CELERY_WORKER_CONCURRENCY`     | `2`     | worker            | Parallel tasks (general queue)    |
| `CELERY_PROCESSING_CONCURRENCY` | `1`     | processing-worker | Parallel book scrapes             |

---

## Server sizing guide

### Minimum (2 CPU / 4 GB RAM)

Good for low traffic + occasional book processing.

```env
BACKEND_MEM_LIMIT=600m
BACKEND_CPU_LIMIT=1.0
WORKER_MEM_LIMIT=400m
WORKER_CPU_LIMIT=0.5
PROCESSING_WORKER_MEM_LIMIT=1200m
PROCESSING_WORKER_CPU_LIMIT=1.5
REDIS_MEM_LIMIT=320m
REDIS_CPU_LIMIT=0.3
REDIS_MAXMEMORY=256mb

GUNICORN_WORKERS=2
CELERY_WORKER_CONCURRENCY=1
CELERY_PROCESSING_CONCURRENCY=1
```

Reserved for host OS + Postgres: ~1.5 GB. Total container allocation: ~2.5 GB.

---

### Recommended (4 CPU / 8 GB RAM)

Handles active readers + background book processing in parallel.

```env
BACKEND_MEM_LIMIT=1g
BACKEND_CPU_LIMIT=1.5
WORKER_MEM_LIMIT=600m
WORKER_CPU_LIMIT=0.5
PROCESSING_WORKER_MEM_LIMIT=2500m
PROCESSING_WORKER_CPU_LIMIT=2.0
REDIS_MEM_LIMIT=400m
REDIS_CPU_LIMIT=0.5
REDIS_MAXMEMORY=320mb

GUNICORN_WORKERS=3
CELERY_WORKER_CONCURRENCY=2
CELERY_PROCESSING_CONCURRENCY=1
```

Reserved for host OS + Postgres: ~2 GB. Total container allocation: ~5 GB.

---

### High-performance (8 CPU / 16 GB RAM)

Process multiple large books simultaneously.

```env
BACKEND_MEM_LIMIT=2g
BACKEND_CPU_LIMIT=2.0
WORKER_MEM_LIMIT=1g
WORKER_CPU_LIMIT=1.0
PROCESSING_WORKER_MEM_LIMIT=6g
PROCESSING_WORKER_CPU_LIMIT=4.0
REDIS_MEM_LIMIT=512m
REDIS_CPU_LIMIT=0.5
REDIS_MAXMEMORY=400mb

GUNICORN_WORKERS=4
CELERY_WORKER_CONCURRENCY=4
CELERY_PROCESSING_CONCURRENCY=2
```

Reserved for host OS + Postgres: ~3 GB. Total container allocation: ~9.5 GB.

---

## Why processing-worker needs so much RAM

Book scraping loads an entire book's HTML into Python memory before building
the EPUB. Large books like **বাংলা কোরআন** (2 300+ topics) or
**মহাভারত** (2 000+ topics) can use 2–4 GB per scrape run.

**Disk page-cache** (added to this codebase) saves each page to disk as it is
fetched, so an OOM-killed or restarted worker resumes where it left off
rather than starting from scratch. The cache lives under
`<RUNTIME_STORAGE_DIR>/processing/scrape_cache/` and is deleted automatically
after a successful build. This means even if `PROCESSING_WORKER_MEM_LIMIT` is
set conservatively and the host OOM-killer fires, the next retry will load
already-fetched pages from disk instead of hitting the network again.

**Guideline:** set `PROCESSING_WORKER_MEM_LIMIT` to ~60 % of total host RAM
if you need to process large books reliably without the disk-cache retry loop.
On a 4 GB server that is `~2400m`; on an 8 GB server `~4800m`.

---

## Gunicorn workers

Rule of thumb: `GUNICORN_WORKERS = (2 × CPU cores) + 1`

| Host CPUs | Recommended workers |
| --------- | ------------------- |
| 1         | 2                   |
| 2         | 3                   |
| 4         | 5                   |
| 8         | 9                   |

Each worker is a separate Python process. Each uses roughly
`BACKEND_MEM_LIMIT / GUNICORN_WORKERS` MB after the first request, so keep
`BACKEND_MEM_LIMIT ≥ GUNICORN_WORKERS × 150m`.

---

## Celery worker concurrency

`CELERY_WORKER_CONCURRENCY` controls how many general tasks run in parallel
(email, catalog sync, etc.). These tasks are mostly I/O bound and safe to
run at 2–4 on any server.

`CELERY_PROCESSING_CONCURRENCY` controls simultaneous book scrapes. Keep this
at `1` unless you have a large-RAM server and have set
`PROCESSING_WORKER_MEM_LIMIT` high enough to accommodate N × scrape overhead.

---

## CPU limit meaning

A `cpus` value of `1.0` means the container may use at most one full CPU core
(100 % of one core). A value of `0.5` means 50 % of one core. Values above
the host's physical core count are silently capped by the kernel.

Setting `PROCESSING_WORKER_CPU_LIMIT=2.0` on a 2-core server lets the scraper
use 100 % of both cores during intensive HTML parsing, which is what causes
the current "1–5 % CPU" symptom — the container limit was previously `0` (no
limit) but the _memory_ limit was causing OOM kills before CPU could be
fully used.

---

## How to apply changes

```bash
# 1. Edit deploy/env/app.env (never commit this file — it has secrets)
nano deploy/env/app.env

# 2. Redeploy affected services only (zero-downtime for unchanged services)
cd deploy
docker compose -f compose/docker-compose.yml up -d --no-build \
  backend worker processing-worker

# 3. Verify limits took effect
docker stats --no-stream
```

To also rebuild Docker images (after code changes):

```bash
docker compose -f compose/docker-compose.yml up -d --build \
  backend worker processing-worker
```

---

## Monitoring current usage

```bash
# Live stats for all containers
docker stats

# One-shot snapshot
docker stats --no-stream

# Check if processing-worker was OOM-killed by the host
docker inspect compose-processing-worker-1 \
  --format '{{.State.OOMKilled}} exit={{.State.ExitCode}}'

# Check if container hit its Docker memory limit
docker stats compose-processing-worker-1 --no-stream \
  --format "MEM: {{.MemUsage}}  ({{.MemPerc}})"
```

A container is Docker-OOM-killed when `MemUsage` reaches `MemLimit`.
The host kernel OOM-killer fires when the entire host runs out of memory
(all containers + OS combined). The disk page-cache protects against both.

---

## Common problems and fixes

| Symptom                                  | Likely cause                                | Fix                                                                   |
| ---------------------------------------- | ------------------------------------------- | --------------------------------------------------------------------- |
| CPU stays 1–5 %, never higher            | No CPU-intensive work queued                | Normal at idle; queue a book to verify                                |
| Processing-worker keeps restarting       | OOM kill during large book scrape           | Increase `PROCESSING_WORKER_MEM_LIMIT` or let disk-cache retry finish |
| "Cannot build EPUB: no content chapters" | Source website has no published lessons     | Not a resource issue; the book has no content on ebangla              |
| Gunicorn 504 gateway timeout             | `GUNICORN_TIMEOUT` too low for slow queries | Increase `GUNICORN_TIMEOUT` to 360                                    |
| Redis eviction warnings                  | `REDIS_MAXMEMORY` too low                   | Increase `REDIS_MAXMEMORY` and `REDIS_MEM_LIMIT` by 50 %              |
