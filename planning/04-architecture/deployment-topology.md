# Deployment topology (Docker Compose)

Status: DRAFT

Decision: [ADR-0019](adr/0019-docker-compose-deployment.md) (D-22, D-24), [ADR-0025](adr/0025-six-services-with-gateway.md) (D-31), [ADR-0026](adr/0026-gateway-auth-check-via-identity.md) and D-33 (backup), D-39 (SSR web). **Every part of the system is developed, tested and deployed as its own container under Docker Compose.** No component runs outside a container, in any environment, and no component is started as a thread of another.

## Containers (ten)

| Container | Image built from | Port (internal) | Network(s) | State / volume |
|---|---|---|---|---|
| `caddy` | Caddy (official image, pinned) | 80/443 published | `edge`, `app` | `caddy_data` (certificates) |
| `web` | Angular SSR server on Node (multi-stage build, D-39) | 8080 | `app` | none |
| `gateway` | `svc-gateway` | 8100 | `app` | none |
| `identity` | `svc-identity` | 8101 | `app`, `db` | `identity_files` (profile images, D-44) |
| `catalog` | `svc-catalog` | 8102 | `app`, `db` | `catalog_files` (EPUB, covers) |
| `reader` | `svc-reader` | 8103 | `app`, `db` | `reader_files` (reading copies) |
| `ingestion-api` | `svc-ingestion` (command `api`) | 8104 | `app`, `db` | `ingestion_files` (scrape cache) |
| `ingestion-worker` | `svc-ingestion` (command `worker`, same image; image includes a Java runtime and epubcheck, D-47, approval pending in the P1 dependency batch) | none | `app`, `db`, egress to the source only | `ingestion_files` (shared with `ingestion-api` only) |
| `notify` | `svc-notify` | 8105 | `app`, `db`, egress to SMTP | none |
| `postgres` | PostgreSQL (official image, pinned) | 5432 | `db` | `pgdata` |

One-shot jobs (not part of the ten): `migrate` (per service image, `<svc> migrate`) and `backup` (`pg_dump` per database plus file volume copy). There is no Redis, no Celery and no message broker.

Only `caddy` publishes host ports (HTTPS; port 80 only for the certificate flow: ACME challenge and redirect to HTTPS, D-97). Each service has its own database and role in the single `postgres` container (D-24) and its own file volume where it stores files; a role cannot connect to another service's database and no volume is shared across services (INV-PLT-014). `ingestion-api` and `ingestion-worker` are one service and share its volume and database.

```
Internet ─► caddy (HTTPS, certificate renewal) ─┬► web :8080       Angular SSR            (/)
                                                └► gateway :8100                          (/api/*)
gateway ─► identity /internal/authorize          (every /api/* except public routes)
        ├► identity       /api/identity/*
        ├► catalog        /api/catalog/*
        ├► reader         /api/reader/*
        └► ingestion-api  /api/ingestion/*
notify, ingestion-worker: no route
postgres ◄── each service, own database + role         (network `db`, no route from `edge`)
```

Caddy and the gateway never serve files from disk or volumes; only services stream files after a check. The public routes (sign-in, invite acceptance, password reset, catalog browse/search/detail of metadata only, D-34) skip the identity check and are rate limited by the gateway ([ADR-0026](adr/0026-gateway-auth-check-via-identity.md)). The `web` container reaches the API only through the gateway.

## Networks and isolation

| Network | Members | Rule |
|---|---|---|
| `edge` | caddy | only network with published ports |
| `app` | caddy, web, gateway, all services | service-to-service HTTP; `internal: true` except where egress is listed |
| `db` | postgres, services, backup/migrate | `internal: true`; caddy and web are not members |

Egress: only `ingestion-worker` (source site, GET-only per D-03) and `notify` (SMTP) get outbound access, via a dedicated non-internal network each.

## Per-container rules (INV-PLT-014)

- One process per container; the image's `ENTRYPOINT` is the service binary; PID 1 handles SIGTERM with graceful drain.
- Images: multi-stage builds, minimal runtime base, non-root user, read-only root filesystem, `cap_drop: [ALL]`, `no-new-privileges`; writable paths are explicit volumes or `tmpfs`. Base-image versions are pinned by digest and registered in the [dependency policy](dependency-policy.md).
- The Java runtime of epubcheck raises `ingestion-worker` memory: its `mem_limit` includes the JVM heap cap (to be measured at P1) and epubcheck runs at most one at a time per worker slot.
- Resource limits (`mem_limit`, `cpus`, `pids_limit`) on every container, summing to well under the host memory (budget table produced in P1); a restart policy (`restart: unless-stopped`) on all long-running containers.
- Configuration through environment variables validated at startup (INV-PLT-001); **secrets are files** (Compose secrets under `/run/secrets`, read-only; the source-site cookie is one such file mounted into the ingestion containers and rotatable without a rebuild), never in images, environment values, logs or a committed `.env`; deploy never prints them ([secrets](../10-security/secrets-and-keys.md)); full secret inventory: [../10-security/secrets-and-keys.md](../10-security/secrets-and-keys.md).
- Health: every service serves `/health/live` and `/health/ready` (INV-PLT-007); Compose `healthcheck` uses `ready`; `depends_on: condition: service_healthy` orders startup (postgres → migrate → identity → other services → gateway → web → caddy).
- Logs: JSON to stdout/stderr only; the Docker logging driver rotates them (size and file count bounded).
- Background work: ingestion jobs run only in `ingestion-worker`; event consumers (reader, ingestion, catalog, notify) run as a task group inside their service container pulling `GET /internal/events`; no work runs inside an HTTP request.

## Compose files

| File | Use |
|---|---|
| `deploy/compose/compose.yaml` | the full system, production-shaped (all containers above) |
| `deploy/compose/compose.dev.yaml` | override for development: bind-mounted source, watch/rebuild, debug logging, published ports for `caddy` only (a local certificate), mail sink container, fake-clock environment flag |
| `deploy/compose/compose.test.yaml` | override for CI: ephemeral volumes, seeded data, fixed ports for the E2E runner container |

Every command a developer needs is a wrapper over `docker compose` in `xtask` (`xtask up`, `xtask test`, `xtask reset`); nothing requires Rust, Node or Postgres installed on the host except to edit code (builds happen in containers).

## Environments

| Env | Purpose | Data |
|---|---|---|
| local (dev) | developer; **the full container set** via `compose.yaml` + `compose.dev.yaml`; synthetic seed; mail sink and fake clock as dev-only containers/flags | synthetic seed |
| ci | `compose.test.yaml`; ephemeral Postgres container per run; contract, model and gold gates | fixtures, gold corpus |
| staging | the same `compose.yaml` and images as production, separate host/project name | synthetic seed (nothing is migrated, D-32) |
| production | users, launched fresh (users re-invited, books re-ingested, D-32) | real |

Dev, staging and production run the **same images and the same `compose.yaml`**; only the override file and secrets differ.

## Release and rollback

- CI builds each image once, tags it with the git SHA and pushes it to a registry (choice in the dependency register; a private registry or an archive transferred to the host).
- A release is identified by **image digest**: a `compose.yaml` pinned to digests (`release.env` holding the SHA and digests); no `latest` tags. Deploy = pull images → run `migrate` containers (expand phase, forward-only) → `docker compose up -d --wait` (health-gated; a **rolling restart**, one service at a time, never `down` then `up`) → smoke test.
- Rollback = redeploy the previous release's digests. Migrations stay backward compatible for one release (expand/contract), so the old images run on the new schema.
- Failed health gate within the timeout → automatic redeploy of the previous digests.

## Capacity assumptions (verified in P0)

Under 5,000 books, under 50 users (D-29), ≤ 50 rps public, ≤ 4 concurrent ingestion jobs, EPUB ~ 5–50 MB/book. One host, one PostgreSQL, no cache layer, sized for the sum of container `mem_limit`s plus headroom (budget table is produced in P1). **Monthly** full backup (D-33): `pg_dump` of every database plus a copy of every file volume, copied off the host, and a restore drill ([backup-restore](../11-operations/backup-restore.md)); up to 30 days of data can be lost (reading progress, review decisions, user changes since the last backup; books can be re-ingested).
