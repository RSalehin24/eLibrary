# Receiving-machine setup

Commands below are for a POSIX shell from the repository root unless a different
directory is shown. They describe the isolated development reference, not a
production deployment. Inspect existing services first; do not start the entire
legacy Compose stack, processing workers, scheduler or delivery workers.

## Runtime and dependencies

Use Python **3.12** and Node **22.18 or newer within the approved Node 22 runtime**.
The former host had Python 3.12.13 and Node 22.20.0. PostgreSQL 16, a separate test
Redis server and Docker/Compose support the existing verification tools. Give the
Docker VM adequate resources as well as the host; the former VM had only 2 CPU /
2 GiB. No new inference model or hardware capacity has been established.

Dependency sources are `app/backend/requirements-dev.txt` (includes runtime
requirements), `app/backend/constraints.txt`, and `app/web/package-lock.json`.
Use existing approved pins; no upgrades are necessary for the move.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -c app/backend/constraints.txt -r app/backend/requirements-dev.txt
```

From `app/web`:

```sh
npm ci
npx playwright install chromium firefox webkit
```

On Linux use the matching system prerequisites required by the approved Playwright
installation, or its approved container. Do not ignore missing browser libraries.
The exact approved browser/image pins and known ESLint exception are recorded in
[verification tooling](../../architecture/verification-tooling.md). This document
does not approve new packages/versions or bypassing peer/audit checks.

## Reference infrastructure

The prior foundation project uses `local/compose/docker-compose.yml` with
`local/compose/platform-test.yml`, project `elibrary-foundation`. Start **only** its
PostgreSQL service after checking context, ports, environment and existing volumes:

```sh
docker compose -p elibrary-foundation -f local/compose/docker-compose.yml -f local/compose/platform-test.yml up -d postgres
```

Its reference default is DB `bangla_library`, loopback port **55432**. Credentials
must match your private settings. On a new empty reference database:

```sh
PYTHONPATH=app/backend .venv/bin/python app/backend/manage.py migrate
PYTHONPATH=app/backend .venv/bin/python app/backend/manage.py check
PYTHONPATH=app/backend .venv/bin/python app/backend/manage.py makemigrations --check --dry-run
```

Export the reference environment below **before** those commands. Do not migrate
the separate user preview as part of setup. Pytest requires permission to create
its separate `test_bangla_library` DB. The seed guard intentionally requires
`bangla_library` on 55432; do not weaken it to accommodate other data.

Run a dedicated Redis instance at **127.0.0.1:56380**, without persistence, for
these isolated tests. With the existing `redis-server` executable:

```sh
redis-server --bind 127.0.0.1 --port 56380 --save "" --appendonly no
```

Keep this foreground process in its own terminal. Do not point tests at another
application's Redis or flush unrelated instances. Separate Redis server instances,
not merely different database numbers, are required for engine Pub/Sub isolation.
RabbitMQ/worker integration and live-source tests need their separately scoped
setup later; starting them is not necessary to inspect the website.

## Private shell environment

Create a mode-0600 private shell file outside version control and source it in
each relevant terminal. Replace the DB credential placeholder and storage path.
Use a newly generated private `DJANGO_SECRET_KEY`; do not reuse the development
default for a public installation. These values reproduce the reference setup:

```sh
export APP_ENV=development
export PYTHONPATH=app/backend
export DATABASE_URL='postgresql://<user>:<url-encoded-password>@127.0.0.1:55432/bangla_library'
export MEDIA_ROOT='/absolute/new/project/test-artifacts/foundation/implementation-reference-media'
export REDIS_HOST='redis://127.0.0.1:56380/0'
export REDIS_URL='redis://127.0.0.1:56380/0'
export CELERY_BROKER_URL='redis://127.0.0.1:56380/0'
export CELERY_TASK_ALWAYS_EAGER=false
export SOURCE_SITE_HOST=source.example.test
export FRONTEND_BASE_URL=http://127.0.0.1:3001
export EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
export EMAIL_HOST=127.0.0.1
export EMAIL_PORT=1025
export EMAIL_USE_TLS=false
export ACCOUNT_INVITE_FROM_EMAIL=library@example.test
export DEFAULT_FROM_EMAIL=library@example.test
export FOUNDATION_WEB_URL=http://127.0.0.1:3001
export FOUNDATION_API_URL=http://127.0.0.1:8002
export FOUNDATION_CANONICAL_ORIGIN=https://library.example.test
```

Set the private secret separately without printing it. Both engine Redis overrides
must be full URLs, not a bare hostname. `SOURCE_SITE_HOST` here is synthetic;
real source/corpus collection needs the correct private configuration and explicit
live verification. Loopback SMTP configuration makes request readiness truthful;
leave delivery workers off. No external mail or Kindle arrival is authorized.

## Build and serve the latest source

API, separate terminal with the reference environment loaded:

```sh
.venv/bin/python app/backend/manage.py runserver 127.0.0.1:8002 --noreload
```

From `app/web`, with no Next.js server/PWA test using its build directory:

```sh
npm run lint
npm test
npm run typecheck
API_INTERNAL_URL=http://127.0.0.1:8002 PUBLIC_SITE_URL=https://library.example.test npm run build
HOSTNAME=127.0.0.1 PORT=3001 API_INTERNAL_URL=http://127.0.0.1:8002 PUBLIC_SITE_URL=https://library.example.test npm run start
```

**Supply API origin and canonical URL at startup as well as build time.** Earlier
attempts missing runtime configuration produced invalid evidence. The startup
command uses the packaged standalone artifact. Keep it unchanged during PWA/update
tests; do not run development and production servers on the same port/build tree.
The API uses `--noreload`: restart it deliberately after backend changes.

Readiness checks from another terminal:

```sh
curl --fail http://127.0.0.1:8002/api/v1/health/live/
curl --fail --output /dev/null http://127.0.0.1:3001/catalog/
```

## Fresh browser fixtures

Use the maintained isolated runner; it creates private fixtures per specification:

```sh
.venv/bin/python tests/web/run_isolated.py --project chromium --artifacts test-artifacts/foundation/new-machine-smoke login.spec.mjs linked-entity-permissions.spec.mjs
```

The artifact directory must not already exist. Project choices are `chromium`,
`firefox`, `webkit`, `android`, `ios`. The runner uses the approved pinned Linux
container for Firefox; it mounts source read-only and private artifacts writable.
Its host-loopback forwarding uses `FOUNDATION_WEB_URL` and `FOUNDATION_API_URL`.

Run specs sequentially. Do not seed while a different run enumerates the global
sitemap or relies on the same source/discovery/queue state. Existing development
LocMem login/password-link quotas persist across requests in one API process;
restart the **identified reference API** between complete runs rather than disable
throttles. Investigate quota exhaustion within a full run with actual HTTP status
evidence; it is not yet a confirmed explanation for all recorded failures.
