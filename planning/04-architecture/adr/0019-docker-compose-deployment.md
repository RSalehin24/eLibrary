# ADR-0019 — Everything runs as separate containers under Docker Compose

Status: ACCEPTED

## Context
The earlier plan allowed systemd units or Compose, release directories with a symlink switch, and a local mode that ran all services in one process (D-07). The owner now requires the whole application to be developed inside Docker Compose and deployed as a Docker Compose stack in which every part runs in its own container (2026-11-18, D-22).

## Decision
- Every component of [the topology](../deployment-topology.md) is a container: `caddy`, `web`, `identity`, `catalog`, `reader`, `ingestion-api`, `ingestion-worker`, `notify` and `postgres` (nine containers, [ADR-0020](0020-five-services-no-gateway.md)), plus one-shot `migrate` and `backup` jobs. There is no gateway and no Redis.
- Development, CI, staging and production use the same images and the same `compose.yaml`; overrides differ only in dev conveniences and secrets.
- Edge proxy: **Caddy** (D-23; forward-auth per [ADR-0024](0024-caddy-forward-auth-deny-by-default.md)). PostgreSQL: **one container** holding one database and role per service (D-24); ADR-0003 (database per service) is satisfied logically by separate databases and roles.
- The "all services in one process" local mode and systemd/symlink releases are removed. Releases are image digests; rollback is redeploying the previous digests.
- Domain services are never published on host ports; only `caddy` publishes 80/443.

## Consequences
+ One reproducible environment everywhere; "works on my machine" differences vanish; service isolation (network, filesystem, resources) is enforceable and testable.
+ Matches the microservice boundary: independent build, restart and scaling per service.
− More memory and build time than one process; mitigated by multi-stage builds, cached layers, per-container limits and a budget table (P1).
− Docker and Compose become required tooling (system packages need owner approval per the dependency policy).
− Stateful volumes (Postgres, catalog assets, reading copies, scrape cache) need explicit backup/restore handling ([backup-restore](../../11-operations/backup-restore.md)).
− The consolidation escape hatch (co-deploying services) is now a Compose change (one container running two binaries is still disallowed; consolidation means merging the crates into one service).
