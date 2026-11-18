# Local Development Assets

This folder contains the local Docker development stack, local env templates, runtime scratch files, and helper scripts used during day-to-day development.

## Folder Layout

- `local/compose/`: local Docker Compose definition
- `local/docker/`: local backend/frontend Dockerfiles
- `local/env/`: local env template and generated local env file
- `local/runtime/`: local runtime scratch files such as the Celery beat schedule
- `local/scripts/`: local stack control and env generation helpers

## Primary Entry Points

- `local/scripts/dev.sh up` : Start the local stack with Docker Compose watch
- `local/scripts/dev.sh down` : Stop the local stack
- `local/scripts/generate-env.sh` : Generate the local env file
- `local/scripts/dev.sh --help` : Show script usage

Every non-help run of `local/scripts/dev.sh` prints the effective super admin email and password used by the local stack.
Compose commands load `local/env/.env` directly into the shell environment before invoking Docker Compose, so secret values containing `$` are passed literally without generating a second env file.

## Docker Compose Watch

Starting local development through either of these entry points runs Docker Compose with `--watch`:

- `local/scripts/dev.sh up`
- `./run_local.sh`

By default, `local/scripts/dev.sh up` and `./run_local.sh` expose the dev ports on your LAN IP so the app is reachable from another device on the same network. Use `LOCALHOST_ONLY=1` if you explicitly want localhost-only access for a session.

The watch rules are defined in `local/compose/docker-compose.yml`. If your Compose CLI shows interactive watch shortcuts while attached, watch is already enabled for the standard local workflow.

Default watch behavior:

- `backend` syncs `app/backend/` into the container and Django autoreload applies code changes
- `worker` syncs `app/backend/apps/` and `app/backend/config/`, then restarts the container when those files change
- `beat` syncs `app/backend/apps/` and `app/backend/config/`, then restarts the container when those files change
- `frontend` syncs `app/frontend/` into the container and Vite hot reload applies UI changes
- `backend`, `worker`, and `beat` rebuild when `app/backend/requirements.txt` or `app/backend/requirements-dev.txt` changes
- `frontend` rebuilds when `app/frontend/package.json` or `app/frontend/package-lock.json` changes

## Runtime Model

The default local stack starts:

- `postgres`
- `redis`
- one-shot `backend-init` bootstrap for migrations and super admin seeding
- `backend` with Docker Compose sync plus Django autoreload
- `worker` with Docker Compose sync-and-restart rules
- `beat` with Docker Compose sync-and-restart rules
- `frontend` with Docker Compose sync plus Vite hot reload

## Related Docs

- Local development guide: [docs/operations/local-development.md](../docs/operations/local-development.md)
- Tests overview: [tests/README.md](../tests/README.md)
