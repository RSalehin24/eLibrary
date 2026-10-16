# Bengali library platform deployment

The new platform uses `deploy/compose/platform.yml`, separate from the retained
Vite/Redis-worker deployment. The approved images build successfully and have
passed isolated local Linux container checks over HTTPS. Production
deployment, certificate/account setup, and external mail delivery require their
separate authorization; this guide does not perform them.

## Approved images and builds

| Image | Purpose |
| --- | --- |
| `python:3.12.15-slim-bookworm` | API, migrations, dispatcher, scheduler, workers |
| `node:22.23.3-bookworm-slim` | Next.js build and standalone frontend |
| `nginx:1.30.6-alpine` | TLS routing and protected bytes |
| `rabbitmq:4.3.6-management` | Confirmed persistent task transport |

The Python/Node major versions match the approved application runtime. These
exact patch tags are listed by the publisher's official image manifests:
[Python](https://github.com/docker-library/official-images/blob/master/library/python),
[Node](https://github.com/docker-library/official-images/blob/master/library/node),
[Nginx](https://github.com/docker-library/official-images/blob/master/library/nginx),
and [RabbitMQ](https://github.com/docker-library/official-images/blob/master/library/rabbitmq).
Image downloads and isolated builds/tests were explicitly approved on 16 October 2026.
PostgreSQL and Redis use the already installed, approved images pinned by digest
in the Compose file. All four approved downloads are now also pinned by digest.
RabbitMQ has a stable node hostname so its persisted queues remain available
after container replacement. Record final application and downloaded image digests in
the release report after the isolated build passes.

Python production requirements now pin the already installed AnyMail 15.2 and
chardet 5.2.0 versions. `app/backend/constraints.txt` was generated with the
existing virtual environment's `pip freeze --exclude-editable`. Docker installs
only production requirements under those constraints. The frontend uses its
approved lockfile with `npm ci`. Development audit findings remain documented in
[verification tooling](../architecture/verification-tooling.md).

## Prepare a host

Use a supported Ubuntu/Debian host with Docker Engine and Compose v2 or later. No cloud
provider is required. Allow inbound HTTPS and HTTP for the configured domain;
keep PostgreSQL, Redis, RabbitMQ, API, and frontend container ports private.
Provide a valid certificate chain and private key for the chosen hostname.

Generate a new environment without printing credentials:

```sh
python3 deploy/prepare_environment.py --hostname library.your-domain.example
```

This exclusively creates `deploy/platform.env` with mode 0600. It generates
separate database administrator, application database, Redis, RabbitMQ, and Django
secrets and a canonical `PUBLIC_SITE_URL`. Existing files are preserved. The hostname is normalized to ASCII IDNA
and validated; environment values cannot inject extra lines. Keep this file
outside source control and encrypted in the deployment backup.

Set `TLS_DIRECTORY` to a private certificate directory containing `fullchain.pem`
and `privkey.pem`. Bind paths must be visible to the Docker host; on Colima use
its shared home directory rather than macOS temporary directories. Set
`PUBLIC_SITE_URL` to the public HTTPS origin, including its port when using an
alternate HTTPS port. `HTTP_PORT` and `HTTPS_PORT` control host bindings. The
proxy validates the origin and preserves it in HTTP redirects and canonical URLs.
Configure SMTP variables before account mail or Kindle use:
`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`ACCOUNT_INVITE_FROM_EMAIL`, and `EMAIL_USE_TLS`. Source discovery needs
`SOURCE_SITE_HOST`, optionally `SOURCE_SITE_CATALOG_URL` and fallback hosts.
Authenticated source cookies, when required, belong in the protected runtime
volume; use the existing source-auth preparation procedure without logging them.

Validate the configuration with `docker compose --env-file deploy/platform.env
-f deploy/compose/platform.yml config --quiet`. Avoid printing the expanded
configuration because it contains credentials.

## Start an approved deployment

After image installation and target deployment approval, build and start:

```sh
docker compose --env-file deploy/platform.env -f deploy/compose/platform.yml up -d --build
```

The one-shot initialization service migrates PostgreSQL and collects maintenance
static files. Serving processes wait for successful initialization. A separate
static publisher retains earlier Next.js files and rejects conflicting bytes
under an existing immutable filename. The API/frontend use non-root accounts,
read-only filesystems, temporary scratch directories, and explicit shared volumes.
Nginx workers receive the media read group and a 65,536-file descriptor limit.
Only the proxy publishes host ports. Its upstreams refresh Docker DNS records
after API/frontend replacement without requiring a proxy reload.
Its external surface contains `/api/v1/`, maintenance admin, public pages, and
static files; legacy API routes and direct protected/media requests return 404.

Create the first administrator interactively after startup:

```sh
docker compose --env-file deploy/platform.env -f deploy/compose/platform.yml exec api python manage.py createsuperuser
```

Sign in through the new workspace and configure the authenticator in Profile.
Maintenance admin requires a verified authenticator session. Deployment does not
reset administrator passwords or seed a public demo account. Production settings
reject short/default secrets, debug/eager execution, insecure cookies, HTTP or
mixed public origins, wildcard hosts, weak database credentials, a non-AMQP or
guest broker, and an unauthenticated cache. Demo login is disabled in production.
The production Django router also excludes legacy API endpoints, independently
of the proxy routing rule. Production disables the legacy engine's Redis signal
listeners and rejects enabling them. Development retains compatibility behavior.
Celery uses durable control/reply queues with expiry and exclusive event queues;
RabbitMQ 4.3 rejects the older transient non-exclusive queue defaults. See
[RabbitMQ queue durability](https://www.rabbitmq.com/docs/queues) and
[Celery control configuration](https://docs.celeryq.dev/en/stable/userguide/configuration.html#control-queue-durable).

## Concurrency and resources

The defaults are configuration starting points, not measured capacity claims.
API workers/threads (`API_WORKERS=4`, `API_THREADS=4`) are independent of processing
and delivery concurrency (two processes each). Increase them only from measured
CPU, memory, latency, and connection use. Per-container defaults are 2 GiB API,
2 GiB processing, 1 GiB delivery, and 1 GiB frontend. PostgreSQL, RabbitMQ, the OS,
and filesystem cache need additional memory; document the actual benchmark host.

Budget PostgreSQL connections for every API thread, each worker child, dispatcher,
scheduler, initialization, and operator connection. The initial application
budget is roughly 16 serving + 4 worker + 2 daemon connections, plus transient
initialization and operational headroom. Heartbeat threads and administrative
commands add connections; measure the peak before scaling replicas. Keep the sum
below PostgreSQL's configured maximum with recovery/maintenance headroom.

Redis is disposable, bounded at 256 MiB with no eviction. It holds shared request
limits and optional Celery results; durable accounts, permissions, jobs, and
reading state remain in PostgreSQL. Cache failures leave authoritative catalog
and session reads available; quota-protected commands return bounded 503 errors.
RabbitMQ and PostgreSQL have persistent volumes. The dispatcher can retain work
while the broker is unavailable. New schedules use their own scheduler service;
the legacy Celery beat and processing engine are not part of this stack.

API readiness checks PostgreSQL at `/api/v1/health/ready/`; liveness performs no
database access at `/api/v1/health/live/`. Health output contains no credentials or
version details. Nginx records request IDs, method, status, timings, and byte
counts without request paths, query strings, or reader identifiers.

## Shutdown, updates, and storage

Use Compose `stop` for a controlled shutdown. The API has 30 seconds to finish
requests, workers have 75 seconds, and the scheduler/dispatcher handle termination
between bounded ticks. Their signal handlers restore previous handlers after
exit. Interrupted jobs recover through attempt fences and saved checkpoints.
Local live checks covered a broker outage with confirmed retry, queued-message
survival after broker container replacement, duplicate
delivery, stale-attempt recovery, cache loss/recovery, and replacement of both
serving containers without restarting the proxy.

Back up the environment, PostgreSQL, media, runtime checkpoints, and certificates
together. Keep publication bytes and their database references consistent by
stopping writers/dispatcher/scheduler/workers during a filesystem/database backup
unless using coordinated snapshots. Use `pg_dump` custom format through the
PostgreSQL container and archive the media/runtime volumes without exposing them
through HTTP. Store backups away from the host and verify checksums.

Restore into a separate, empty Compose project first. Restore database roles and
the database dump with the matching PostgreSQL tooling, restore media/runtime with
the application UID/GID 10001, and apply migrations before allowing traffic.
Check permissions, a protected chapter/download, reading progress, outstanding
jobs, and a paused-job resume. A backup is accepted only after this restore drill.
Do not overwrite a running database or delete volumes during routine updates.

Retain previous frontend static files for existing sessions. The publisher never
deletes them; monitor disk use and plan an explicitly approved retention cleanup.
Multiple-host deployment requires shared media/runtime/static storage before
adding replicas. Public SSR/API reads currently bypass reusable response caches,
so publication changes are read from PostgreSQL across frontend instances; there
is no instance-local public-page cache to invalidate.

Reproducible local checks are in `tests/deployment/`: `compose_client.py` creates
guarded synthetic fixtures, `verify_platform.py` checks the HTTPS surface and
live preparation, `verify_recovery.py` checks interruptions, and
`verify_restore.py` captures a consistent backup and restores it into a separate
empty project. Set `DEPLOYMENT_TEST_DIRECTORY` to a private directory containing
the test `platform.env`, `tls/fullchain.pem`, and generated `fixture.json`.
The scripts refuse non-test project names and origins; they never reset a database
or delete persistent volumes. Fixtures require the explicit test marker and
`https://library.example.test:18443`. Supply local self-signed certificates only
for this isolated hostname. Certificate validation remains enabled in HTTPS checks.

The local machine is a MacBookAir10,1 with 8 GiB memory and eight host CPU cores;
its ARM64 Colima Linux VM has two CPUs and 2 GiB memory, without swap. Run one full
test stack at a time. The restore drill stops the source test stack while the
restored stack is active, then returns to the source. Concurrent full stacks
exhausted this VM's memory; this is not capacity acceptance infrastructure.

Active preparation-worker SIGKILL and normal lease recovery passed alongside
the stale-heartbeat recovery check. The user's subsequent simulator-only scope
is also verified: actual Docker-package installation in Ubuntu/Debian containers
(systemd startup simulated), accepted install/relaunch/reinstall signals,
loopback mail, synthetic relevance, browser lab timing, and measured k6 HTTPS
load. See [simulator acceptance](simulator-acceptance.md). Physical/staging checks
and production capacity claims are outside that scope.
