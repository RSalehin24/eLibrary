# Persisted jobs and EPUB preparation

Logical operations, execution attempts, and broker dispatch records have separate
models. The new worker prepares EPUBs, submits configured Kindle requests, and
sends [queued account links](account-mail.md). Database constraints distinguish
asset jobs from account jobs; account mail is excluded from processing-only APIs.
See [Kindle delivery](kindle-delivery.md) for address outcomes and SMTP boundaries. The existing
source-processing system remains available during the transition.

## Commands and administration

Global processing management or staff/full-control access is required for job
lists/details/controls, book asset summaries, and preparation commands. Ownership
and book-scoped metadata/processing grants do not grant global job management.
Book-edit links are derived separately from the existing metadata permission
query. Lists default to 50 records, cap at 100, and use creation-time/UUID ordering.
Query counts remain bounded as page size grows. Details include the latest
twenty attempts.

`POST /api/v1/manage/assets/<uuid>/prepare/` requires a client-generated
`operation_id` and the asset's `expected_updated_at`. A transaction creates the
job and its dispatch together. Repeating the identical identifier returns the
same operation; reusing it for another request returns 409. The response includes
202, `operation_id`, and `status_url`. Serving requests do not extract books,
publish to the broker, or execute Celery work.

`/api/v1/manage/jobs/` supports state/kind/book filters and bounded pagination.
`/api/v1/manage/jobs/<uuid>/` provides details and revision-checked controls.
Concurrent changes return `409 state_conflict`. Running pause/cancel requests
remain distinct from confirmed stopped states until a processing boundary.
Resume creates a new generation. Terminal operations cannot resume. The API
omits raw inputs, checkpoint contents, and storage paths. It exposes real stages,
timestamps, bounded error codes, checkpoint availability, and valid actions.
Session CSRF and backend permissions apply; responses are private/no-store/noindex.

`/manage/jobs/` provides filters, ordinary pagination, mobile cards, and details.
Authorized processors can request ready EPUB preparation from book management.
Active work refreshes every two seconds, idle views every fifteen seconds, and
failed reads back off to sixty seconds. Hidden tabs suspend polling; slow reads
do not overlap. Mutations never replay automatically. After an uncertain
preparation request, the UI links to its original operation so the outcome can
be inspected before another request is issued.

## Dispatch and recovery

The dispatcher leases at most fifty records per tick. AMQP publication uses
durable messages, publisher confirmation, bounded connection/confirmation
timeouts, and dispatch identifiers only. Heavy work uses `processing`; the
Kindle and account mail use `delivery`. Non-AMQP transport and an AMQP URL
incorrectly used as a Celery result backend are rejected before leasing work.
Broker interruptions leave dispatches pending with bounded backoff. Expired
leases can be reclaimed; stale confirmations cannot overwrite another lease.

Workers claim attempts transactionally. Duplicate/stale deliveries cannot claim
active or terminal operations. Completion, checkpoints, and failures must match
the active attempt and generation. Transient failures retry from fifteen seconds
with a five-minute cap and a bounded failure budget. Permanent failures are
visible. Uncertain outcomes require attention and never retry automatically.
Pause-only attempts do not consume the failure budget. These are at-least-once
semantics, not exactly-once execution.

Reconciliation repairs missing dispatches, republishes confirmed but unstarted
work after sixty seconds, and recovers heartbeats older than three minutes.
Heartbeat values are checked again under the attempt lock. An interrupted
Kindle or account-mail attempt at `sending` requires review because SMTP acceptance could already
have happened. That safety state and loopback SMTP behavior are tested; live
RabbitMQ transport and Kindle-device arrival remain unverified.

## EPUB worker and operations

The worker checks current account status/global processing permission, book
deletion, and the pinned ready-asset revision before and after preparation.
Invalid archives/missing assets fail permanently; storage interruptions retry
within the failure budget. Prepared publications are checksum-addressed and
reusable, and extraction publishes files atomically.

One bounded EPUB is currently one processing unit. Pause/cancel is cooperative
before/after that unit. A separate connection commits a heartbeat every fifteen
seconds while extraction holds its publication transaction. Heartbeat failures
prevent recording success. A stale worker's prepared artifact can be reused,
but its completion cannot overwrite recovered work. No percentage is invented.

Configure the database, shared protected storage, an AMQP `CELERY_BROKER_URL`,
and an explicit supported `CELERY_RESULT_BACKEND`, such as Redis, through the
application's secure environment. PostgreSQL job state is authoritative;
Celery results are disposable. From the backend directory:

```sh
python manage.py dispatch_background_jobs --interval 2
python manage.py dispatch_background_jobs --once
celery -A config.celery worker --queues processing --concurrency 2
```

`--once` performs one bounded maintenance/dispatch tick. Dispatch intervals accept
1–60 seconds. `BACKGROUND_JOB_SOFT_TIMEOUT_SECONDS` defaults to 3600 and accepts
60–86400; the hard timeout adds sixty seconds. Configure worker concurrency
independently of serving concurrency. Each long job can use two database
connections: processing and heartbeat. Include both in connection budgets.
Celery uses late acknowledgement, worker-loss redelivery, prefetch one, and
existing process/memory recycling. Workers and dispatcher require the same
database/asset storage before scaling across hosts. Retain prior prepared assets
for existing reader sessions.

## Verification boundary

PostgreSQL tests cover atomicity/idempotency, authorization/CSRF/revisions,
query bounds, concurrent claims/dispatchers, checkpoints, stale completions,
retry limits, leases, and recovery. Worker tests prepare real local EPUB fixtures
and cover pause/resume, replacements/revocation, independent heartbeat commits,
interruptions, and the registered Celery task. Publisher tests use injected
applications; they do not prove live broker behavior. Chromium checks exercise
phone controls, conflicts, polling, URL errors, and responsive layouts.

The [RabbitMQ proposal](reliability-dependencies.md) awaits approval; its image
has not been installed. Live broker interruption, source discovery/automation
integration, duplicate/incomplete source resolution, live queued delivery, portable
production deployment, supported browsers, physical devices, and capacity
measurements remain outstanding. This increment does not complete the admin
or reliability phase.
