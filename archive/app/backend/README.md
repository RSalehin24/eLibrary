# Backend

This folder contains the Django API, Celery worker and beat entrypoints, and the ingestion, catalog, and access services.

## Local Development

Use the repo-level guide in [docs/operations/local-development.md](../../docs/operations/local-development.md). The default local workflow runs the backend through the Docker Compose watch-enabled development stack.

## Runtime Notes

- App code: `app/backend/apps/`
- Django config: `app/backend/config/`
- Runtime storage: `app/backend/storage/`
- Tests: `tests/backend/`
- Pytest config: `tests/pytest.ini`

## Django Apps

| App          | Purpose                                                                     |
| ------------ | --------------------------------------------------------------------------- |
| `accounts`   | Custom user model, email-based auth, Kindle email storage, TOTP setup state |
| `access`     | Per-book permission grants, access tokens, permission scopes                |
| `catalog`    | Book, Contributor, Series, Category, BookGroup models; EPUB/HTML assets     |
| `ingestion`  | Source catalog sync, scraper, book processing pipeline, Celery tasks        |
| `processing` | Processing job lifecycle, queue management, service modules                 |
| `common`     | Shared utilities: text normalization, base models, helpers                  |

## Container Targets

- [local/docker/backend.Dockerfile](../../local/docker/backend.Dockerfile): local autoreload image with dev dependencies
- [deploy/docker/backend.Dockerfile](../../deploy/docker/backend.Dockerfile): production Gunicorn/Celery image
