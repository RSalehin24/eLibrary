# ADR-0019 — Everything runs as separate containers under Docker Compose

Status: ACCEPTED

Basis: D-22, D-24, D-31 (container list), D-33 (monthly backup), D-39 (SSR web).

## Context
The earlier plan allowed systemd units or Compose, release directories with a symlink switch, and a local mode that ran all services in one process (D-07). The owner requires the whole application to be developed inside Docker Compose and deployed as a Docker Compose stack in which every part runs in its own container (2026-11-18, D-22).

## Decision
- Every component of [the topology](../deployment-topology.md) is a container: `caddy`, `web`, `gateway`, `identity`, `catalog`, `reader`, `ingestion-api`, `ingestion-worker`, `notify` and `postgres` (ten containers, [ADR-0025](0025-six-services-with-gateway.md)), plus one-shot `migrate` and `backup` jobs. There is no Redis, no Celery and no message broker.
- Development, CI, staging and production use the same images and the same `compose.yaml`; overrides differ only in dev conveniences and secrets.
- Edge proxy: **Caddy**, for HTTPS and certificate auto-renewal only (D-23 as narrowed by D-31); authentication is the gateway's job ([ADR-0026](0026-gateway-auth-check-via-identity.md)). `web` is an Angular SSR server on Node (D-39). PostgreSQL: **one container** holding one database and role per service (D-24); ADR-0003 is satisfied logically by separate databases and roles.
- The "all services in one process" local mode and systemd/symlink releases are removed. Releases are image digests; a deploy restarts one service at a time (never `down` then `up`); rollback is redeploying the previous digests.
- Secrets are files mounted into containers (Compose secrets), never environment variables in images or committed files; every container has memory and process limits and a restart policy.
- Backups are monthly (D-33): a full dump of every database plus the file volumes, copied off the host, with a restore drill; up to 30 days of data may be lost.
- Domain services are never published on host ports; only `caddy` publishes 80/443; port 80 serves only the ACME challenge and the redirect to HTTPS (D-97).

## Consequences
+ One reproducible environment everywhere; service isolation (network, filesystem, resources) is enforceable and testable.
+ Matches the microservice boundary: independent build, restart and scaling per service.
− More memory and build time than one process; mitigated by multi-stage builds, cached layers, per-container limits and a budget table (P1).
− Docker and Compose become required tooling (system packages need owner approval per the dependency policy).
− Stateful volumes (Postgres, catalog files, reading copies, scrape cache, profile images) need explicit backup/restore handling ([backup-restore](../../11-operations/backup-restore.md)).
− Monthly backups leave a wide data-loss window (D-33); the assistant may recommend a higher frequency later.
− The consolidation escape hatch means merging crates into one service; a container running two binaries is still disallowed.
