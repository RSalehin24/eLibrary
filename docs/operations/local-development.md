# Local Development

## Prerequisites

- Docker Compose with `up --watch` support
- Node/npm available locally for frontend build and Playwright verification

## Folder Layout

- `app/`: backend and frontend application code
- `local/compose/`: local Docker Compose stack with `develop.watch` rules
- `local/docker/`: local Dockerfiles for backend and frontend
- `local/env/`: local env template and generated local env file
- `local/runtime/`: runtime files created by local services, such as the Celery beat schedule
- `local/scripts/`: local stack and env generation helpers
- `tests/`: root-level backend and frontend automated tests
- `tests/scripts/`: test runners and deterministic E2E data helpers

## Environment Setup

Generate the local env file:

```bash
local/scripts/generate-env.sh
```

The local stack reads `local/env/.env`. Update values there as needed.
Compose commands load `local/env/.env` directly into the shell environment before invoking Docker Compose, so secret values containing `$` are passed literally without generating a second env file.

The effective super admin email and password are printed by `local/scripts/dev.sh` on every non-help run. If the env file leaves either value blank, the local Docker Compose defaults are `admin@example.com` and `changeme`.

## Start The Local Stack

```bash
local/scripts/dev.sh up
```

`local/scripts/dev.sh up` is the supported way to start local development with Docker Compose watch enabled. `./run_local.sh` is a thin wrapper around the same command.

By default, the local stack is reachable from another device on the same Wi-Fi when you start it through either entrypoint:

```bash
local/scripts/dev.sh up
```

Because `./run_local.sh` is only a wrapper, the same applies there:

```bash
./run_local.sh
```

The script detects your Mac's active LAN IP, binds the frontend and backend on `0.0.0.0`, and rewrites the effective frontend/backend base URLs for that session so a phone or tablet can open the same dev stack.

If you explicitly want localhost-only access, use:

```bash
LOCALHOST_ONLY=1 ./run_local.sh
```

The script runs the local stack through `docker compose up --build --watch` or `docker-compose up --build --watch`, depending on what is available on your machine. The watch rules live in `local/compose/docker-compose.yml`.

If your Compose CLI shows interactive watch shortcuts while attached, watch is already enabled for this workflow. You do not need to press `w` separately when starting the stack through `local/scripts/dev.sh up`.

This starts:

- `postgres`
- `redis`
- one-shot `backend-init` bootstrap for migrations and super admin seeding
- `backend` with Compose sync and Django autoreload
- `worker` with Compose sync-and-restart
- `processing-worker` with Compose sync-and-restart (dedicated worker for CPU-heavy book scraping)
- `beat` with Compose sync-and-restart
- `frontend` with Compose sync and Vite hot reload

Watch behavior:

- `backend` syncs `app/backend/` into `/app`, and Django's built-in autoreloader applies backend code changes
- `worker` syncs `app/backend/apps/` and `app/backend/config/` into `/app`, then restarts when those Python files change
- `processing-worker` syncs `app/backend/apps/` and `app/backend/config/` into `/app`, then restarts when those Python files change
- `beat` syncs `app/backend/apps/` and `app/backend/config/` into `/app`, then restarts when those Python files change
- `frontend` syncs `app/frontend/` into `/app`, and Vite hot reload applies UI changes
- `backend`, `worker`, `processing-worker`, and `beat` rebuild when `app/backend/requirements.txt` or `app/backend/requirements-dev.txt` changes
- `frontend` rebuilds when `app/frontend/package.json` or `app/frontend/package-lock.json` changes

Default URLs:

- Frontend: `http://127.0.0.1:5173`
- Backend API: `http://127.0.0.1:8000`

When started normally, the script prints LAN URLs such as `http://192.168.0.104:5173` and `http://192.168.0.104:8000`. If autodetection picks the wrong interface, set `RUN_LOCAL_INTERFACE=en0` before the command.

Books, uploads, and static assets are stored only under `app/backend/storage/`.

## Common Commands

```bash
local/scripts/dev.sh ps
local/scripts/dev.sh logs frontend
local/scripts/dev.sh logs backend
tests/scripts/seed-e2e-data.sh
tests/scripts/test-all.sh
tests/scripts/test-backend.sh
tests/scripts/test-frontend-unit.sh
tests/scripts/test-e2e.sh
local/scripts/dev.sh restart backend
local/scripts/dev.sh down
```

Each repo-facing helper in `local/scripts/` and `tests/scripts/` supports `-h` or `--help` for usage details without starting the stack or a test run.

## Confirm Watch Behavior

Start the stack with `local/scripts/dev.sh up`, then use these commands while editing source files:

```bash
local/scripts/dev.sh logs backend
logs/scripts/show-logs.sh frontend
```

The attached `local/scripts/dev.sh up` session shows Docker Compose watch events such as syncs and rebuilds. `local/scripts/dev.sh logs backend` follows the grouped Docker Compose logs for `backend`, `worker`, and `beat`, which lets you confirm Django reloads and Celery restarts after Compose watch updates. `logs/scripts/show-logs.sh frontend` tails the Vite dev server log so you can confirm frontend hot reload behavior after frontend syncs.

## Verification

Run the full verification pass against the real Dockerized application:

```bash
tests/scripts/verify.sh
```

Repeat it multiple times when you want extra confidence:

```bash
tests/scripts/verify.sh --repeat 3
```

`tests/scripts/verify.sh`:

- starts or refreshes the live local stack through `local/scripts/dev.sh up`
- waits for the frontend and backend to become healthy
- reseeds deterministic browser data through `tests/scripts/seed-e2e-data.sh`
- runs backend `pytest` inside the backend container using `tests/pytest.ini`
- runs frontend unit tests from `tests/frontend/unit/`
- runs the frontend production build inside the frontend container
- runs Playwright against the live app on `http://127.0.0.1:5173`

The Playwright config and live browser stories live under:

- `tests/frontend/playwright.config.js`
- `tests/frontend/e2e/`

The separate test entrypoints are:

- `tests/scripts/test-backend.sh`
- `tests/scripts/test-frontend-unit.sh`
- `cd app/frontend && npm run build`
- `tests/scripts/test-e2e.sh`
