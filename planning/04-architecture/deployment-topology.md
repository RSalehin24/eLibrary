# Deployment topology

Status: DRAFT

Target: one Linux host (decision D-07), reproducible with a single script.

```
Internet ─► Nginx/Caddy (TLS, HTTP/2, static cache)
              └► gateway :8080
                   ├► web :3000
                   ├► identity :8101   access :8102   catalog :8103
                   ├► content :8104    library :8105  ingestion :8106  notify :8107
PostgreSQL 16 :5432   (databases: identity, access, catalog, content, library, ingestion, notify)
Artifact store: /var/lib/elibrary/artifacts (content-addressed)
Search index:   /var/lib/elibrary/search     (catalog; derived, rebuildable)
```

## Process model

- Each service: a systemd unit (or Compose service) with its own user, working directory, resource limits (CPU/memory/file descriptors), restart policy `on-failure`.
- Internal services bind to `127.0.0.1` or a private network; only the gateway is reachable from the proxy (INV-GWY-001).
- Workers (ingestion jobs, outbox relay, notify sender) run in the same binary as a separate task group, enabled by flag, so they can be moved to separate processes without code changes.

## Environments

| Env | Purpose | Data |
|---|---|---|
| local | developer; **all services in one process** via `xtask dev` with embedded fakes (fake clock, local mail sink) | synthetic seed |
| ci | ephemeral Postgres per test; contract + model + gold gates | fixtures, gold corpus |
| staging | production-shaped, same deploy script | anonymized snapshot of migrated data |
| production | users | real |

## Release

Immutable release directories (`/opt/elibrary/releases/<git-sha>`), a `current` symlink,
forward-only migrations applied by a pre-start step, health-gated switch, one-command rollback
(symlink back; migrations are backward compatible for one release — expand/contract).

## Capacity assumptions (verified in P0)

~2,000 books, tens of readers, ≤ 50 rps public, ≤ 10 concurrent ingestion jobs, artifacts ~ 5–50 MB/book.
