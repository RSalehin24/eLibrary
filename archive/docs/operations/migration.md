# Migration

## What The Migration Script Automates

`migration/migrate.sh` moves a live production deployment from one server to another (for example, from AWS to DigitalOcean). It is a four-phase pipeline with progress markers so any phase can be resumed after an interruption.

It performs these steps:

1. **Preflight** — validates SSH access, sudo rights, disk space on both machines, source stack health, target port availability, and optional DNS/edge readiness.
2. **Snapshot** — freezes the source stack (stops beat, backend, frontend), captures a PostgreSQL dump, Redis dump, app code archive, and storage tree with SHA-256 checksums, then restarts the source stack.
3. **Restore** — uploads the snapshot bundle to the target, wipes and recreates the target stack, restores Postgres, Redis, and storage, runs migrations, and verifies row counts match the source.
4. **Verify** — confirms all target services are healthy, optionally configures host Nginx and Certbot, and confirms HTTPS reachability.

## Folder Layout

- `migration/migrate.sh`: main entrypoint
- `migration/migrate_steps/`: phase implementation scripts
- `migration/env/`: migration config template and generated config file
- `migration/lib/`: shared helpers (config, logging, SSH, bundle, compose)
- `migration/runtime/`: local staging area for snapshot bundles (created at runtime)

## Prepare Config

Generate the migration config file:

```bash
cp migration/env/migrate.env.example migration/env/migrate.env
```

Then fill in the new server details in `migration/env/migrate.env`:

```
TARGET_USER=<target-ssh-user>
TARGET_IP=<new-server-ip>
```

**Most values are reused automatically from `deploy/env/.host.env`** — the source host, SSH user, remote app directory, domain, certbot email, ports, Docker version, and Nginx version are all inherited. Only set a key in `migrate.env` when it differs on the new server.

### Config Reference

| Key                           | Default                          | Description                                                                               |
| ----------------------------- | -------------------------------- | ----------------------------------------------------------------------------------------- |
| `TARGET_USER`                 | inherits `DEPLOY_USER_NAME`      | SSH user on the target server.                                                            |
| `TARGET_IP`                   | —                                | **Required.** IP address of the target server.                                            |
| `TARGET_USER`                 | inherits `DEPLOY_USER_NAME`      | SSH user on the target server.                                                            |
| `TARGET_REMOTE_APP_DIR`       | inherits `DEPLOY_REMOTE_APP_DIR` | App directory on the target server.                                                       |
| `TARGET_PUBLIC_BASE_URL`      | inherits `PUBLIC_BASE_URL`       | Override if the domain changes.                                                           |
| `TARGET_PUBLIC_API_ORIGIN`    | inherits `PUBLIC_API_ORIGIN`     | Override if the domain changes.                                                           |
| `TARGET_FRONTEND_BASE_URL`    | inherits `FRONTEND_BASE_URL`     | Override if the domain changes.                                                           |
| `SOURCE_PORT`                 | `22`                             | SSH port on the source server.                                                            |
| `TARGET_PORT`                 | `22`                             | SSH port on the target server.                                                            |
| `DRAIN_TIMEOUT_SECONDS`       | `900`                            | How long to wait for in-flight tasks to finish before freezing the source.                |
| `HEALTHCHECK_TIMEOUT_SECONDS` | `240`                            | How long to wait for target services to become healthy.                                   |
| `KEEP_SOURCE_DOWN_ON_SUCCESS` | `0`                              | Set to `1` to leave the source stack stopped after a successful migration.                |
| `ALLOW_TARGET_RESET`          | `0`                              | Set to `1` to allow wiping existing data on the target (required for a non-empty target). |
| `SKIP_EDGE_SETUP`             | `0`                              | Set to `1` to skip Nginx/Certbot setup on the target.                                     |

### SSH Access Requirements

Both the source and target must allow passwordless SSH from your local machine:

```bash
ssh-copy-id ubuntu@<source-ip>
ssh-copy-id ubuntu@<target-ip>
```

Both must also have passwordless `sudo`:

```bash
# On each server:
echo 'ubuntu ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/ubuntu
```

### Local Tool Requirements

The script requires these tools locally: `bash`, `ssh`, `scp`, `tar`, `gzip`, `python3`, and `sha256sum` (or `shasum` on macOS).

## Run Migration

### Dry run (no changes)

Always start with a dry run to validate config and print what would happen:

```bash
migration/migrate.sh --dry-run
```

### Preflight only (safe, read-only)

Check SSH, disk space, and source health without touching anything:

```bash
migration/migrate.sh --phase preflight
```

### Full migration

```bash
migration/migrate.sh
```

This runs all four phases end-to-end: preflight → snapshot → restore → verify.

### Individual phases

Run phases separately when you want to validate each step before proceeding:

```bash
migration/migrate.sh --phase preflight
migration/migrate.sh --phase snapshot
migration/migrate.sh --phase restore
migration/migrate.sh --phase verify
```

### Resume after interruption

If the migration fails or is interrupted, resume from where it left off:

```bash
migration/migrate.sh --resume
```

`--resume` picks up the most recent bundle in `migration/runtime/` and skips any phase already marked as complete.

### Resume a specific phase

Combine `--phase` and `--resume` to rerun only one phase using an existing bundle:

```bash
migration/migrate.sh --phase restore --resume
migration/migrate.sh --phase verify --resume
```

### Skip edge setup

When DNS has not been pointed at the new server yet, skip Nginx/Certbot:

```bash
migration/migrate.sh --skip-edge
```

After pointing DNS at the target, finish the edge setup:

```bash
migration/migrate.sh --phase verify --resume
```

### Custom config file

```bash
migration/migrate.sh --config /path/to/other-migrate.env
```

### Keep the local staging bundle

By default the local bundle is deleted on success. To retain it for inspection:

```bash
migration/migrate.sh --keep-staging
```

### Allow wiping an existing target

If the target already has a live stack with data that should be replaced:

```bash
migration/migrate.sh --allow-target-reset
```

## Phase Details

### Preflight

- Checks SSH connectivity and passwordless sudo on both servers.
- Checks available disk space locally and on the target.
- Checks source Docker Compose stack health.
- Checks target ports are available (backend and frontend).
- Checks whether the target app directory already has data and enforces `--allow-target-reset` if so.
- Checks DNS for the target domain if provided.
- No changes are made to either server. Safe to run multiple times.

### Snapshot

- Waits up to `DRAIN_TIMEOUT_SECONDS` for in-flight Celery tasks to finish.
- Stops `beat`, `backend`, and `frontend` on the source to freeze writes. `postgres`, `redis`, `worker`, and `processing-worker` remain running during the dump.
- Captures a gzipped PostgreSQL dump (`pg_dumpall`) and a Redis RDB dump.
- Archives the app code (excluding storage) and the full storage tree as separate tarballs.
- Records row counts, table hashes, storage file counts, and Redis key counts into a metadata manifest with SHA-256 checksums.
- Restarts the source stack after the dump completes (unless `KEEP_SOURCE_DOWN_ON_SUCCESS=1`).
- All files land in `migration/runtime/<bundle-id>/`.

### Restore

- Uploads the snapshot bundle to `/tmp/<bundle-id>` on the target.
- Verifies SHA-256 checksums before restoring.
- Resets the target Docker stack (`down --volumes`) and starts `postgres` and `redis`.
- Restores the PostgreSQL dump, Redis RDB, and storage tree.
- Syncs the app code and env onto the target.
- Applies any `TARGET_*` env overrides (domain, public URLs).
- Runs `docker compose up -d --build` and waits for health checks.
- Compares post-restore row counts and storage file counts against the source manifest.

### Verify

- Confirms all containers are healthy on the target.
- Re-validates data summaries against the source manifest.
- Configures host Nginx and issues a Certbot TLS certificate if DNS resolves to the target.
- Confirms HTTPS reachability at `https://<domain>/` and `https://<domain>/api/csrf/`.
- Cleans up the remote bundle directory on success.

## Migration Log

Every run writes a timestamped log to `migration/runtime/<bundle-id>/migration.log`. Review it for detailed output on any failed step.

## After Migration

1. Verify the application is reachable and working at the new URL.
2. Update `deploy/env/.host.env` to point `DEPLOY_IP` at the new server so future deployments go to the right target.
3. Decommission or stop the old source server.
