# Deployment

## What The Deployment Script Automates

`deploy/scripts/deploy.sh` is the primary deployment entrypoint. It is designed for an Ubuntu-style remote host with passwordless `sudo`.

It performs these steps:

1. Validates DNS, SSH, and sudo access.
2. Syncs the target branch to the remote app directory.
3. Syncs the local workspace to the remote host.
4. Merges non-empty keys from the selected local env file into the remote app env.
5. Installs or upgrades Docker when required.
6. Recreates the Docker Compose frontend and backend stack.
7. Installs/configures host Nginx and Certbot.
8. Verifies Nginx config loading and HTTPS reachability.

## Folder Layout

- `deploy/compose/`: production Docker Compose definition
- `deploy/docker/`: production Dockerfiles and Nginx container config
- `deploy/env/`: deployment env templates and generated env files
- `deploy/scripts/`: remote deployment and host bootstrap scripts
- `app/`: application code synchronized to the remote host
- `automation/`: shared env and shell helpers reused by local and deploy workflows

## Prepare Env Files

Generate or extend the needed env files:

```bash
deploy/scripts/generate-env.sh production
deploy/scripts/generate-env.sh test
deploy/scripts/generate-env.sh host
```

Every repo-facing helper in `deploy/scripts/` supports `-h` or `--help` for usage details without starting a deployment or host change.

Files involved:

- `deploy/env/app.env.example`: shared application template for deployed stacks
- `deploy/env/.production.env`: production application/runtime values used for env sync
- `deploy/env/.test.env`: optional test deployment runtime values
- `deploy/env/host.env.example`: deploy host template
- `deploy/env/.host.env`: deploy host settings for SSH, Docker, and Nginx automation
- Remote `deploy/env/.app.env`: generated remote runtime env after sync/merge

Important deploy host settings in `deploy/env/.host.env`:

- `DEPLOY_USER_NAME`
- `DEPLOY_IP`
- `DEPLOY_BRANCH_NAME`
- `DEPLOY_DOMAIN`
- `DEPLOY_CERTBOT_EMAIL`
- `DEPLOY_NGINX_CONF_DIR`
- `DEPLOY_NGINX_CONFIG_NAME`
- `DEPLOY_NGINX_VERSION`
- `DEPLOY_DOCKER_VERSION`
- `DEPLOY_ENV_SYNC_MODE`

## Run Deployment

Default production deployment:

```bash
deploy/scripts/deploy.sh
```

On the first successful deployment to a given remote app directory, the script prints the configured super admin email and password once and tells you to note them down. Later deploy runs do not show those credentials again.

Deploy using a different env file name:

```bash
deploy/scripts/deploy.sh --env-name test
```

Force or skip env sync:

```bash
deploy/scripts/deploy.sh --sync-mode push
deploy/scripts/deploy.sh --sync-mode preserve
deploy/scripts/deploy.sh --sync-mode prompt
```

## Env Sync Behavior

- The script merges only non-empty keys from the selected local env file into remote `deploy/env/.app.env`.
- Existing remote keys remain untouched unless the local env file provides a non-empty replacement.
- Deployment commands load `deploy/env/.app.env` directly into the shell environment before invoking Docker Compose, so secret values containing `$` are preserved literally without generating a second env file.
- When a local or remote env file needs attention, the script offers a 5-second edit window and continues if you do nothing.
- Docker is installed automatically when missing, or upgraded when `DEPLOY_DOCKER_VERSION` is set and the remote version does not match.
- Host Nginx config is written automatically and Nginx is installed or upgraded when `DEPLOY_NGINX_VERSION` is set and the remote version does not match.

## Updating Runtime Configuration Without a Full Redeploy

For configuration-only changes (e.g. increasing `CELERY_PROCESSING_CONCURRENCY`) you can push the updated env and restart only the affected service, avoiding a full stack teardown.

### Option A — Live, zero-downtime concurrency change (current session only)

Celery's prefork pool accepts a `pool_grow` control command while workers are running:

```bash
source deploy/env/.host.env
TARGET="${DEPLOY_USER_NAME}@${DEPLOY_IP}"
REMOTE_DIR="${DEPLOY_REMOTE_APP_DIR:-/home/${DEPLOY_USER_NAME}/library_app}"

# Add 2 processes to the processing-worker pool
ssh "$TARGET" "cd '$REMOTE_DIR' && \
  docker compose -f deploy/compose/docker-compose.yml exec -T processing-worker \
  celery -A config control pool_grow 2"
```

This takes effect immediately. The change is lost on the next container restart.

### Option B — Persistent change via deploy.sh (recommended)

1. Update the value in `deploy/env/.production.env` (e.g. `CELERY_PROCESSING_CONCURRENCY=6`).
2. Run the deployment script with `--sync-mode push`:

```bash
deploy/scripts/deploy.sh --sync-mode push
```

This rebuilds and recreates all containers. In-flight tasks are interrupted but **redelivered** on restart because `task_acks_late=True` is set in the Celery config, so no tasks are lost.

**Memory note:** each processing worker process can consume up to ~400 MB (`worker_max_memory_per_child`). The `processing-worker` container is capped by `PROCESSING_WORKER_MEM_LIMIT`. Raise that limit alongside `CELERY_PROCESSING_CONCURRENCY` if needed.

## Remote Runtime Model

- Docker Compose runs `frontend`, `backend`, `worker`, `beat`, `postgres`, `redis`, and a one-shot `backend-init` bootstrap service.
- `backend-init` applies migrations and seeds the super admin before `backend`, `worker`, and `beat` start.
- Host Nginx proxies `/` to the frontend container and `/api/` plus `/admin/` to the backend container port bound on localhost.
- Static and media files are served from `app/backend/storage/` on the remote host.
- Workspace sync excludes local runtime files, local env files, gitignored logs, virtualenvs, and other generated artifacts.
