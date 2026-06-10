# Bangla Library Platform

[![License](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Stack-blue?logo=docker)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Node](https://img.shields.io/badge/Node-22-339933?logo=node.js&logoColor=white)](https://nodejs.org/)

A full-stack platform that scrapes, processes, and serves Bangla (and English) ebooks — producing clean EPUB and HTML files for an authenticated library of users.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Deployment](#deployment)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## Features

| Feature | Description |
|---------|-------------|
| **Ebook Scraping** | Automatically pulls ebooks and their metadata — title, author, category, cover — from a Bengali ebook source site. |
| **Book Processing** | Users submit a source URL; the system scrapes, builds, and delivers a ready-to-read EPUB in the background. |
| **Catalog Sync** | Keeps the local library in sync with the source site, detecting new releases and tracking unfinished books. |
| **Ebook Generation** | Produces well-structured EPUB and HTML files with proper chapters, table of contents, and cover art. |
| **Library & Reader** | A searchable library with category filters, an in-browser reader, EPUB downloads, and Kindle delivery. |
| **Access Control** | Granular per-book permissions — who can preview, read, download, or manage each book. |
| **Authentication** | Email-based login with invite-only accounts, TOTP two-factor auth, and self-service password reset. |
| **Automated Testing** | 42+ end-to-end browser tests, a backend pytest suite, and frontend unit tests — all runnable with one command. |
| **Dockerized Stack** | Full local and production environments via Docker Compose — Postgres, Redis, Django, Celery, and React. |
| **One-Command Deploy** | Remote deployment with Nginx and Certbot for TLS, fully automated. |

> Each feature is backed by detailed documentation. See the [Documentation](#documentation) section for deep dives.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend API | Django 5.2 + Django REST Framework (Python 3.12) |
| Task Queue | Celery 5.6 + Redis 7 |
| Processing Worker | Dedicated Celery worker for CPU-heavy book scraping |
| Frontend | React 18 + Vite 5 (JavaScript) |
| Database | PostgreSQL 16 |
| Containerization | Docker Compose |
| Edge / TLS | Nginx 1.27 + Certbot |
| Testing | pytest · node --test · Playwright |

---

## Quick Start

```bash
git clone https://github.com/your-org/elibrary.git && cd elibrary
local/scripts/generate-env.sh
local/scripts/dev.sh up
```

The frontend will be available at `http://localhost:5173` and the backend API at `http://localhost:8000`.

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Git

### Local Development

```bash
# 1. Generate local environment files
local/scripts/generate-env.sh

# 2. Start the full local stack (postgres, redis, backend, worker, beat, frontend)
local/scripts/dev.sh up
```

The frontend will be available at `http://localhost:5173` and the backend API at `http://localhost:8000`.

---

## Project Structure

```
elibrary/
├── app/                    # Application source code
│   ├── backend/            #   Django backend (API, models, Celery tasks)
│   └── frontend/           #   React + Vite frontend
├── tests/                  # Backend pytest + Playwright E2E + frontend unit tests
├── local/                  # Local Docker Compose, Dockerfiles, env templates, scripts
├── deploy/                 # Production Docker Compose, Dockerfiles, deploy scripts
├── migration/              # Database migration tooling between environments
├── automation/             # Shared shell and env helpers for local, deploy, and logs
├── docs/                   # Architecture specs, operations guides, processing docs
├── logs/                   # Local and remote log streaming
└── test-artifacts/         # Test data and audit JSON
```

---

## Testing

All tests require a live Docker stack. Run `local/scripts/dev.sh up` first.

| Command | What it runs |
|---------|--------------|
| `tests/scripts/test-all.sh` | Full suite — backend, frontend unit, and E2E |
| `tests/scripts/test-backend.sh` | Backend pytest only |
| `tests/scripts/test-frontend-unit.sh` | Frontend unit tests only |
| `tests/scripts/test-e2e.sh` | Playwright browser tests only |
| `tests/scripts/seed-e2e-data.sh` | Seed deterministic E2E data |
| `tests/scripts/verify.sh --repeat 3` | Verify the full suite N times |

See [tests/README.md](tests/README.md) for the full coverage map and browser story list.

---

## Deployment

```bash
# Generate production environment files
deploy/scripts/generate-env.sh production
deploy/scripts/generate-env.sh host

# Deploy to remote server
deploy/scripts/deploy.sh
```

See [docs/operations/deployment.md](docs/operations/deployment.md) for the full deployment guide.

---

## Key Commands

| Command | Purpose |
|---------|---------|
| `local/scripts/dev.sh up` | Start local Docker stack |
| `deploy/scripts/deploy.sh` | Deploy to production |
| `logs/scripts/show-logs.sh backend remote` | Stream remote backend logs |
| `logs/scripts/show-logs.sh worker remote` | Stream remote worker logs |
| `logs/scripts/show-logs.sh beat remote` | Stream remote beat logs |

All scripts support `-h` / `--help` for usage details.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Local development guide](docs/operations/local-development.md) | Setting up and running the local Docker environment |
| [Deployment guide](docs/operations/deployment.md) | Production deployment with Nginx and Certbot |
| [Migration guide](docs/operations/migration.md) | Moving data between environments |
| [Authentication flows](docs/operations/authentication-flows.md) | Login, registration, and TOTP 2FA behavior |
| [Log viewing guide](docs/operations/log-viewing.md) | Streaming and viewing application logs |
| [EPUB pipeline specification](docs/epub-pipeline-specification.md) | Detailed EPUB generation pipeline reference |
| [Source site metadata notes](docs/ingestion/source-site-metadata.md) | Metadata extraction from the source site |
| [Test suite overview](tests/README.md) | Full test coverage map and browser story list |

---

## Contributing

Contributions are welcome. Please open an issue first to discuss what you would like to change, then submit a pull request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-change`)
3. Make your changes and add tests
4. Run the full test suite (`tests/scripts/test-all.sh`)
5. Commit and push your branch
6. Open a pull request

---

## License

This project is licensed under the GNU Affero General Public License v3.0. See [LICENSE](LICENSE) for details.
