# Deployment topology (Docker Compose)

Status: DRAFT

Decision: [ADR-0019](adr/0019-docker-compose-deployment.md) (D-22…D-24) and [ADR-0020](adr/0020-five-services-no-gateway.md) (D-27). **Every part of the system is developed, tested and deployed as its own container under Docker Compose.** No component runs outside a container, in any environment, and no component is started as a thread of another.

## Containers (nine)

| Container | Image built from | Port (internal) | Network(s) | State / volume |
|---|---|---|---|---|
| `caddy` | Caddy (official image, pinned) | 80/443 published | `edge`, `app` | `caddy_data` (certificates) |
| `web` | Angular static files (multi-stage build, served by a minimal static server) | 8080 | `app` | none |
| `identity` | `svc-identity` | 8101 | `app`, `db` | none |
| `catalog` | `svc-catalog` | 8102 | `app`, `db` | `catalog_files` (EPUB, covers) |
| `reader` | `svc-reader` | 8103 | `app`, `db` | `reader_files` (reading copies) |
| `ingestion-api` | `svc-ingestion` (command `api`) | 8104 | `app`, `db` | `ingestion_files` (scrape cache) |
| `ingestion-worker` | `svc-ingestion` (command `worker`, same image) | none | `app`, `db`, egress to the source only | `ingestion_files` (shared with `ingestion-api` only) |
| `notify` | `svc-notify` | 8105 | `app`, `db`, egress to SMTP | none |
| `postgres` | PostgreSQL (official image, pinned) | 5432 | `db` | `pgdata` |

One-shot jobs (not part of the nine): `migrate` (per service image, `<svc> migrate`) and `backup` (`pg_dump` per database plus file volume copy). There is no gateway, no Redis, no Celery and no message broker.

Only `caddy` publishes host ports. Each service has its own database and role in the single `postgres` container (D-24) and its own file volume where it stores files; a role cannot connect to another service's database and no volume is shared across services (INV-PLT-014). `ingestion-api` and `ingestion-worker` are one service and share its volume and database.

```
Internet ─► caddy (TLS, HTTP/2) ─┬► web :8080                           (/)
                                 ├─ forward-auth ─► identity /internal/authorize   (every /api/* except public routes)
                                 ├► identity       /api/identity/*
                                 ├► catalog        /api/catalog/*
                                 ├► reader         /api/reader/*
                                 └► ingestion-api  /api/ingestion/*
notify, ingestion-worker: no public route
postgres ◄── each service, own database + role         (network `db`, no route from `edge`)
```

Caddy never serves files from disk or volumes; only services stream files after a check. The public routes (sign-in, invite acceptance, password reset, demo sign-in POST, catalog public browse/search/preview) skip forward-auth and are rate limited ([ADR-0024](adr/0024-caddy-forward-auth-deny-by-default.md)).

## Networks and isolation

| Network | Members | Rule |
|---|---|---|
| `edge` | caddy | only network with published ports |
| `app` | caddy, web, all services | service-to-service HTTP; `internal: true` except where egress is listed |
| `db` | postgres, services, backup/migrate | `internal: true`; caddy and web are not members |

Egress: only `ingestion-worker` (source site, GET-only per D-03) and `notify` (SMTP) get outbound access, via a dedicated non-internal network each.

## Per-container rules (INV-PLT-014)

- One process per container; the image's `ENTRYPOINT` is the service binary; PID 1 handles SIGTERM with graceful drain.
- Images: multi-stage builds, minimal runtime base, non-root user, read-only root filesystem, `cap_drop: [ALL]`, `no-new-privileges`; writable paths are explicit volumes or `tmpfs`. Base-image versions are pinned by digest and registered in the [dependency policy](dependency-policy.md).
- Resource limits (`mem_limit`, `cpus`, `pids_limit`) on every container; a restart policy (`restart: unless-stopped`) on all long-running containers.
- Configuration through environment variables validated at startup (INV-PLT-001); secrets through Compose secrets (files under `/run/secrets`), never in images or `.env` committed to git ([secrets](../10-security/secrets-and-keys.md)).
- Health: every service serves `/health/live` and `/health/ready` (INV-PLT-007); Compose `healthcheck` uses `ready`; `depends_on: condition: service_healthy` orders startup (postgres → migrate → identity → other services → web → caddy).
- Logs: JSON to stdout/stderr only; the Docker logging driver rotates them (size and file count bounded).
- Background work: ingestion jobs run only in `ingestion-worker`; event consumers (reader, ingestion, catalog, notify) run as a task group inside their service container pulling `GET /internal/events`; no work runs inside an HTTP request.

## Compose files

| File | Use |
|---|---|
| `compose.yaml` | the full system, production-shaped (all containers above) |
| `compose.dev.yaml` | override for development: bind-mounted source, watch/rebuild, debug logging, published ports for `caddy` only, mail sink container, fake-clock environment flag |
| `compose.test.yaml` | override for CI: ephemeral volumes, seeded data, fixed ports for the E2E runner container |

Every command a developer needs is a wrapper over `docker compose` in `xtask` (`xtask up`, `xtask test`, `xtask reset`); nothing requires Rust, Node or Postgres installed on the host except to edit code (builds happen in containers).

## Environments

| Env | Purpose | Data |
|---|---|---|
| local (dev) | developer; **the full container set** via `compose.yaml` + `compose.dev.yaml`; synthetic seed; mail sink and fake clock as dev-only containers/flags | synthetic seed |
| ci | `compose.test.yaml`; ephemeral Postgres container per run; contract, model and gold gates | fixtures, gold corpus |
| staging | the same `compose.yaml` and images as production, separate host/project name | anonymized snapshot of migrated data |
| production | users | real |

Dev, staging and production run the **same images and the same `compose.yaml`**; only the override file and secrets differ.

## Release and rollback

- CI builds each image once, tags it with the git SHA and pushes it to a registry (choice in the dependency register; a private registry or an archive transferred to the host).
- A release is a `compose.yaml` pinned to image digests (`release.env` holding the SHA). Deploy = pull images → run `migrate` containers (expand phase, forward-only) → `docker compose up -d --wait` (health-gated, restart one service at a time, never `down` then `up`) → smoke test.
- Rollback = redeploy the previous release's digests. Migrations stay backward compatible for one release (expand/contract), so the old images run on the new schema.
- Failed health gate within the timeout → automatic redeploy of the previous digests.

## Capacity assumptions (verified in P0)

Under 5,000 books, under 50 users (D-29), ≤ 50 rps public, ≤ 4 concurrent ingestion jobs, EPUB ~ 5–50 MB/book. One host, one PostgreSQL, no cache layer, sized for the sum of container `mem_limit`s plus headroom (budget table is produced in P1). Nightly `pg_dump` plus file volume backup and a restore drill ([backup-restore](../11-operations/backup-restore.md)).
