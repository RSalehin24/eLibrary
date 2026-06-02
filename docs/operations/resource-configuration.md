# Production Resource Configuration

## Why `mem_limit` Was Not Working

The legacy `mem_limit:` key in Compose format v2 is **silently ignored** by the modern
`docker compose` plugin (v2+). Containers ran with no memory cap at all:

```
docker inspect <container> | grep '"Memory"'
# "Memory": 0    ← 0 means unlimited
```

**The fix:** Replace `mem_limit:` with `deploy.resources.limits.memory:`. The `deploy.resources`
block is honoured by `docker compose` in standalone mode (no Swarm needed):

```yaml
# ❌ WRONG — silently ignored by docker compose v2+
mem_limit: ${BACKEND_MEM_LIMIT:-700m}

# ✅ CORRECT — actually enforced via cgroups
deploy:
  resources:
    limits:
      memory: ${BACKEND_MEM_LIMIT:-700m}
```

This is already applied in `deploy/compose/docker-compose.yml`. To verify limits took effect
after a restart:

```bash
docker inspect compose-backend-1 | grep '"Memory"'
# Should show: "Memory": 734003200   (≈ 700 MiB, not 0)

docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
# LIMIT column should now show 700MiB, 600MiB, etc. — not the host total
```

> **Note on macOS / Docker Desktop:** Docker Desktop runs containers inside a Linux VM.
> The VM's total RAM (set in Docker Desktop → Settings → Resources) is the ceiling.
> If the VM is given 2 GB and a container limit is 700 MB, the container sees 700 MB as
> its limit — as expected. Set the VM size to at least the sum of all container limits (~2.5 GB).

---

## Current Server Profile

- **CPU:** Low utilisation — typically 1–5%, spikes to ≤ 50% only during batch processing.
- **RAM:** ≤ 1.6 GB in use out of 3.72 GB available.
- **OS:** Linux (Docker host).

---

## Container Memory Limits

| Service             | `deploy.resources.limits.memory` | Key env var                   | Default value |
| ------------------- | -------------------------------- | ----------------------------- | ------------- |
| `backend`           | 700 MB                           | `BACKEND_MEM_LIMIT`           | `700m`        |
| `worker`            | 600 MB                           | `WORKER_MEM_LIMIT`            | `600m`        |
| `processing-worker` | 900 MB                           | `PROCESSING_WORKER_MEM_LIMIT` | `900m`        |
| `redis`             | 320 MB                           | `REDIS_MEM_LIMIT`             | `320m`        |
| `postgres`          | _(none set)_                     | –                             | –             |

> **Total configured cap:** ~2.52 GB. Postgres uses the remainder (~1.2 GB).
> Actual steady-state RSS is well under each cap.

---

## Worker Concurrency

| Service             | Setting                         | Default | What it controls                          |
| ------------------- | ------------------------------- | ------- | ----------------------------------------- |
| `backend`           | `GUNICORN_WORKERS`              | 2       | Synchronous HTTP worker processes         |
| `backend`           | `GUNICORN_TIMEOUT`              | 120 s   | Kill worker that exceeds this for one req |
| `worker`            | `CELERY_WORKER_CONCURRENCY`     | 2       | Parallel general-purpose Celery tasks     |
| `processing-worker` | `CELERY_PROCESSING_CONCURRENCY` | 1       | Parallel book scraping/processing tasks   |

### Gunicorn workers formula

```
recommended_workers = (2 × CPU_cores) + 1
```

For a 2-core VPS: **5 workers** is the textbook recommendation, but with only 700 MB reserved
for the backend container, stay at **2–3 workers** to avoid OOM kills (each Django worker
~150–250 MB).

### Celery processing concurrency

Book processing is I/O-heavy (many HTTP fetches to ebanglalibrary.com) but each task holds a
large HTML payload in memory. With 900 MB reserved:

- **1 concurrent task** — safe baseline, ~400–600 MB per task.
- **2 concurrent tasks** — possible on 3.72 GB host if no other spike occurs.

> Do **not** raise `CELERY_PROCESSING_CONCURRENCY` above 2 on a 3.72 GB host.

---

## Adding CPU Limits

CPU limits are not currently set (no `cpus:` in docker-compose). To add them:

```yaml
deploy:
  resources:
    limits:
      cpus: "1.0" # max 1 full core
      memory: ${PROCESSING_WORKER_MEM_LIMIT:-900m}
```

CPU limits slow down burst processing without improving stability at current load levels
(≤ 5% CPU normal). Only add them if a runaway task is consuming all CPU.

---

## Recommended `app.env` for 3.72 GB host (conservative/stable)

```dotenv
# Memory limits
BACKEND_MEM_LIMIT=700m
WORKER_MEM_LIMIT=500m
PROCESSING_WORKER_MEM_LIMIT=900m
REDIS_MEM_LIMIT=320m
REDIS_MAXMEMORY=256mb

# Gunicorn (backend HTTP)
GUNICORN_WORKERS=2
GUNICORN_TIMEOUT=120
GUNICORN_MAX_REQUESTS=500
GUNICORN_MAX_REQUESTS_JITTER=50

# Celery workers
CELERY_WORKER_CONCURRENCY=2
CELERY_PROCESSING_CONCURRENCY=1
```

**Total RAM cap:** 700 + 500 + 900 + 320 = **2 420 MB** (~2.4 GB), leaving ~1.3 GB for
Postgres, the OS, nginx, and headroom.

---

## Recommended `app.env` for 3.72 GB host (performance/faster processing)

Use these if RAM stays comfortably below 1.6 GB and you want faster parallel book processing:

```dotenv
BACKEND_MEM_LIMIT=700m
WORKER_MEM_LIMIT=600m
PROCESSING_WORKER_MEM_LIMIT=1400m
REDIS_MEM_LIMIT=320m
REDIS_MAXMEMORY=256mb

GUNICORN_WORKERS=3
GUNICORN_TIMEOUT=180
GUNICORN_MAX_REQUESTS=500
GUNICORN_MAX_REQUESTS_JITTER=50

CELERY_WORKER_CONCURRENCY=2
CELERY_PROCESSING_CONCURRENCY=2
```

> With `CELERY_PROCESSING_CONCURRENCY=2` and `PROCESSING_WORKER_MEM_LIMIT=1400m`, two books
> can be scraped/processed in parallel (~700 MB each). Monitor actual RSS before deploying.

---

## How to Apply Changes

1. Edit `/deploy/env/app.env`.
2. Apply without full downtime:
   ```bash
   cd deploy
   docker compose -f compose/docker-compose.yml --env-file env/app.env up -d \
     backend worker processing-worker redis
   ```
3. Verify limits are now enforced:

   ```bash
   docker inspect compose-backend-1 | grep '"Memory"'
   # Must NOT be 0

   docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
   # LIMIT column must show per-container values, not host total
   ```

---

## Monitoring Memory

```bash
# Per-container usage vs limit
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Host free memory
free -h

# Check if any container was OOM-killed (Memory: -1 means container was killed)
docker inspect compose-processing-worker-1 | grep OOMKilled
```

---

## Notes on Long Books

Books with many chapters (e.g., বাংলা-কোরআন with 114+ surahs) require more memory in the
`processing-worker` container. If such books fail due to OOM or timeout:

1. Increase `PROCESSING_WORKER_MEM_LIMIT` to `1400m` or `1600m`.
2. Check if the container was OOM-killed: `docker inspect compose-processing-worker-1 | grep OOMKilled`
3. Celery tasks run until completion — no explicit `time_limit` is set in `tasks.py`.

- **CPU:** Low utilisation — typically 1–5%, spikes to ≤ 50% only during batch processing.
- **RAM:** ≤ 1.6 GB in use out of 3.72 GB available.
- **OS:** Linux (Docker host).

---

## Container Memory Limits (current production defaults)

| Service             | `mem_limit` (hard cap) | Key env var                   | Default value |
| ------------------- | ---------------------- | ----------------------------- | ------------- |
| `backend`           | 700 MB                 | `BACKEND_MEM_LIMIT`           | `700m`        |
| `worker`            | 600 MB                 | `WORKER_MEM_LIMIT`            | `600m`        |
| `processing-worker` | 900 MB                 | `PROCESSING_WORKER_MEM_LIMIT` | `900m`        |
| `redis`             | 320 MB                 | `REDIS_MEM_LIMIT`             | `320m`        |
| `postgres`          | _(none set)_           | –                             | –             |

> **Total configured cap:** ~2.52 GB. Postgres uses the remainder (~1.2 GB).
> Actual steady-state RSS is well under each cap.

---

## Worker Concurrency

| Service             | Setting                         | Default | What it controls                          |
| ------------------- | ------------------------------- | ------- | ----------------------------------------- |
| `backend`           | `GUNICORN_WORKERS`              | 2       | Synchronous HTTP worker processes         |
| `backend`           | `GUNICORN_TIMEOUT`              | 120 s   | Kill worker that exceeds this for one req |
| `worker`            | `CELERY_WORKER_CONCURRENCY`     | 2       | Parallel general-purpose Celery tasks     |
| `processing-worker` | `CELERY_PROCESSING_CONCURRENCY` | 1       | Parallel book scraping/processing tasks   |

### Gunicorn workers formula

```
recommended_workers = (2 × CPU_cores) + 1
```

For a 2-core VPS: **5 workers** is the textbook recommendation, but with only 700 MB reserved for the backend container, stay at **2–3 workers** to avoid OOM kills (each Django worker ~150–250 MB).

### Celery processing concurrency

Book processing is I/O-heavy (many HTTP fetches to ebanglalibrary.com) but each task holds a large HTML payload in memory. With 900 MB reserved:

- **1 concurrent task** — safe baseline, ~400–600 MB per task.
- **2 concurrent tasks** — possible on 3.72 GB host if no other spike occurs.

> Do **not** raise `CELERY_PROCESSING_CONCURRENCY` above 2 on a 3.72 GB host.

---

## CPU Limits

No explicit CPU limits (`cpus:` / `cpu_quota:`) are set in `docker-compose.yml`. This is intentional:

- Docker's `mem_limit` prevents memory runaway.
- CPU is not a bottleneck at current load levels (≤ 5% normal, ≤ 50% burst).
- Adding CPU quotas would slow down batch processing without improving stability.

To add CPU throttling if needed, insert in `deploy/compose/docker-compose.yml`:

```yaml
services:
  processing-worker:
    cpus: "1.0" # limit to 1 full CPU core
```

---

## Recommended `app.env` for 3.72 GB host (conservative/stable)

```dotenv
# Memory limits
BACKEND_MEM_LIMIT=700m
WORKER_MEM_LIMIT=500m
PROCESSING_WORKER_MEM_LIMIT=900m
REDIS_MEM_LIMIT=320m
REDIS_MAXMEMORY=256mb

# Gunicorn (backend HTTP)
GUNICORN_WORKERS=2
GUNICORN_TIMEOUT=120
GUNICORN_MAX_REQUESTS=500
GUNICORN_MAX_REQUESTS_JITTER=50

# Celery workers
CELERY_WORKER_CONCURRENCY=2
CELERY_PROCESSING_CONCURRENCY=1
```

**Total RAM cap:** 700 + 500 + 900 + 320 = **2 420 MB** (~2.4 GB), leaving ~1.3 GB for Postgres, the OS, nginx, and headroom.

---

## Recommended `app.env` for 3.72 GB host (performance/faster processing)

Use these if RAM stays comfortably below 1.6 GB and you want faster parallel book processing:

```dotenv
BACKEND_MEM_LIMIT=700m
WORKER_MEM_LIMIT=600m
PROCESSING_WORKER_MEM_LIMIT=1400m
REDIS_MEM_LIMIT=320m
REDIS_MAXMEMORY=256mb

GUNICORN_WORKERS=3
GUNICORN_TIMEOUT=180
GUNICORN_MAX_REQUESTS=500
GUNICORN_MAX_REQUESTS_JITTER=50

CELERY_WORKER_CONCURRENCY=2
CELERY_PROCESSING_CONCURRENCY=2
```

> With `CELERY_PROCESSING_CONCURRENCY=2` and `PROCESSING_WORKER_MEM_LIMIT=1400m`, two books
> can be scraped/processed in parallel (~700 MB each). Monitor actual RSS before deploying.

---

## How to Apply Changes

1. Edit `/deploy/env/app.env` (or your production `.env` file).
2. Apply without downtime:
   ```bash
   cd deploy
   docker compose -f compose/docker-compose.yml --env-file env/app.env up -d \
     backend worker processing-worker
   ```
3. Verify new limits took effect:
   ```bash
   docker stats --no-stream
   ```

---

## Monitoring Memory

Check current usage at any time:

```bash
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

Check host free memory:

```bash
free -h
```

Check if any container was OOM-killed:

```bash
docker inspect <container_name> | grep OOMKilled
```

---

## Notes on Long Books

Books with many chapters (e.g., বাংলা-কোরআন with 114+ surahs) require more memory in the
`processing-worker` container. If such books fail due to OOM or timeout:

1. Increase `PROCESSING_WORKER_MEM_LIMIT` to `1400m` or `1600m`.
2. Increase `GUNICORN_TIMEOUT` if the Celery task exceeds the HTTP response timeout
   (unlikely since Celery uses its own timeout separate from Gunicorn).
3. Check Celery task time limits: no explicit `time_limit` or `soft_time_limit` is currently
   set in `tasks.py`, so tasks run until completion unless the worker is restarted.
