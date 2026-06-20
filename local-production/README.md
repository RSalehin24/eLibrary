# Local Production

Runs the elibrary stack locally with production-like settings (Gunicorn, nginx, DEBUG=0), isolated from the development environment.

## Prerequisites

- Docker + Docker Compose
- Docker runtime running (e.g., Colima via `dockerctl start`)

## Quick Start

```bash
# 1. Generate env files from templates
local-production/scripts/generate-env.sh all

# 2. Edit config files
#    local-production/env/app.env              (secrets, database, etc.)
#    local-production/env/local_prod_config.env (ports, branch)

# 3. Deploy
local-production/deploy.sh
```

## Configuration

### `app.env`
Application-level config: secrets, database URL, Celery workers, email, super admin credentials, source site auth.

### `local_prod_config.env`
Instance-level config:

| Variable | Default | Description |
|----------|---------|-------------|
| `FRONTEND_PORT` | `8001` | Host port for the frontend (nginx) |
| `BACKEND_PORT` | `8002` | Host port for the backend (Gunicorn) |
| `GIT_BRANCH` | `main` | Git branch to deploy |
| `COMPOSE_PROJECT_NAME` | `elibrary-local-prod` | Docker Compose project name (isolation) |

URLs and CORS origins are derived from the ports automatically.

## Commands

| Command | Description |
|---------|-------------|
| `deploy.sh` | Info banner, branch check, pull, build, start, health check |
| `deploy.sh up` | Same as above |
| `deploy.sh down` | Stop and remove containers |
| `deploy.sh logs` | Tail logs from all services |
| `deploy.sh logs backend` | Tail logs from a specific service |
| `deploy.sh restart` | Restart all services |
| `deploy.sh ps` | List containers |

### Options

| Option | Description |
|--------|-------------|
| `--branch <name>` | Override git branch |
| `--no-pull` | Skip `git pull` |
| `--no-sleep` | Prevent macOS sleep and keep WiFi alive while stack runs |

## Wake Lock

Keep macOS awake and WiFi connected while the stack is running:

```bash
local-production/deploy.sh up --no-sleep
```

Uses `caffeinate -i` — prevents system idle sleep only (display turns off normally, WiFi stays alive). The wake lock stops automatically when you run:

```bash
local-production/deploy.sh down
```

## Updating

```bash
local-production/deploy.sh
```

This pulls the latest code from the configured branch, rebuilds images, and restarts the stack.
