# Application Code

This folder contains the backend and frontend application code that powers the platform.

## Folder Layout

- `app/backend/`: Django API, Celery worker and beat runtime code, templates, and backend storage
- `app/frontend/`: React and Vite single-page application

## Where To Start

- Backend overview: [app/backend/README.md](backend/README.md)
- Frontend overview: [app/frontend/README.md](frontend/README.md)
- Local development workflow: [docs/operations/local-development.md](../docs/operations/local-development.md)
- Deployment workflow: [docs/operations/deployment.md](../docs/operations/deployment.md)

## Runtime Notes

- Backend tests live under `tests/backend/`
- Frontend unit and browser tests live under `tests/frontend/`
- Runtime storage is rooted at `app/backend/storage/`
- The local Docker stack mounts these app folders directly for watch-enabled development

## Common Commands

```bash
local/scripts/dev.sh up
tests/scripts/test-backend.sh
tests/scripts/test-frontend-unit.sh
tests/scripts/test-e2e.sh
```
