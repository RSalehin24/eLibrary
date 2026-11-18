# Migration

Moves a live production deployment from one server to another using `migration/migrate.sh`.

See the full operations guide: [docs/operations/migration.md](../docs/operations/migration.md)

## Quick Start

```bash
# 1. Create and fill in the config
cp migration/env/migrate.env.example migration/env/migrate.env
# Edit migration/env/migrate.env: set TARGET_USER and TARGET_IP

# 2. Dry run - no changes, validate config only
migration/migrate.sh --dry-run

# 3. Preflight - safe read-only check
migration/migrate.sh --phase preflight

# 4. Full migration
migration/migrate.sh
```

## Common Commands

```bash
# Full migration (all phases)
migration/migrate.sh

# Individual phases
migration/migrate.sh --phase preflight
migration/migrate.sh --phase snapshot
migration/migrate.sh --phase restore
migration/migrate.sh --phase verify

# Resume after interruption
migration/migrate.sh --resume

# Resume a specific phase
migration/migrate.sh --phase restore --resume
migration/migrate.sh --phase verify --resume

# Skip nginx/certbot (DNS not pointed yet)
migration/migrate.sh --skip-edge

# Allow wiping existing target data
migration/migrate.sh --allow-target-reset

# Keep local staging bundle after success
migration/migrate.sh --keep-staging

# Custom config file
migration/migrate.sh --config /path/to/migrate.env
```

## Folder Layout

- `migrate.sh` — main entrypoint
- `migrate_steps/` — phase implementation (preflight, snapshot, restore, verify)
- `env/` — config template and generated config
- `lib/` — shared helpers (config, logging, SSH, bundle, compose)
- `runtime/` — local staging area for snapshot bundles (created at runtime)
