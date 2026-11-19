# Orchestration - job queue, leases, scheduling, publish hand-off

Status: DRAFT (PostgreSQL job queue, ADR-0021; requirements REQ-ING-004, 005, 006, 007, 029, 033, 034)

How work runs. No saga framework, no Redis, no broker, no work inside an HTTP request. Tables: [domain model](../domain-model.md). Transitions and guards: [state machines](../state-machines.md). This page is the operating summary and the failure table.

## Containers

`ingestion-api` serves HTTP and SSE and only inserts rows. `ingestion-worker` (same image, command `worker`) runs the claimer, the executors, the reaper, the scheduler tick, the catalog event consumer and the retention job. Both mount the secret cookie file read-only.

## Job queue

- A job is a row in `jobs`; the next job of a request is inserted in the same transaction as the previous job's success (scrape, curate, duplicate_check, build, publish). Other kinds: `sync`, `check_credential`, `scheduler_tick`, `retention`.
- Claim: `UPDATE ... WHERE id = (SELECT ... WHERE state='queued' AND run_after <= now() ORDER BY priority DESC, run_after, id FOR UPDATE SKIP LOCKED LIMIT 1)` sets `running`, `lease_epoch + 1`, `lease_expires_at = now() + 120 s` (provisional) and `attempt + 1`.
- Lease: the working thread extends it between pages and at step boundaries; a hung thread cannot keep a lease alive. Every executor write carries `AND lease_epoch = $epoch`; a zombie's writes touch zero rows and it stops.
- Reaper (worker, every 30 s, idempotent): `running` with an expired lease goes back to `queued` (attempt below max) or `failed` (`lease_expired`). It is the only time-driven transition.
- Idempotency: each step is safe to run twice; outputs are keyed by input hashes (page URL key, `(request_id, version_no)`, `build_hash`), and `jobs.idempotency_key` is unique. Steps write new output before replacing old.
- Concurrency: worker slots from settings (scrape default 2, one in-flight request per source host) with the page delay; priority manual > reprocess > sync > scheduled recheck.

## Typed errors

Executors return a typed error; the queue decides only from the class, never from message text (table in [domain model](../domain-model.md) section 3). `retryable` and `rate_limited` re-queue with a delay (no sleeping worker); `auth_required` parks the request in `awaiting_credential`; `permanent` fails the job and moves the request to `needs_review` (with the matching review item) or `failed`. A job `succeeded` only means the step ran; the request carries status and outcome, so a failed build can never be reported as success.

## Cancel

The API sets `cancel_requested` on the request and its job. A `queued` job is cancelled at once. A running executor reads the flag before every page and between steps, writes its cursor, and ends `cancelled`; one in-flight HTTP request cannot be interrupted (bounded by its timeout). Long jobs (catalog sync included) have page and error budgets and honour the flag. Cancelling a request that is `done`/`submitted` is refused: reject the version in catalog.

## Sync and automation scheduling

- `scheduler_tick` (one job, every 60 s, claimed like any job) finds due `automation_settings` rows under `FOR UPDATE SKIP LOCKED`, inserts the `sync_runs` row and its `sync` job and moves `next_due_at` to the next slot in the same transaction, so a failure never causes a retry loop and a slot missed during downtime runs once. Exact sequence: [state machines](../state-machines.md) section 5.
- The `sync` job pages through the source listing (bounded, checkpointed per page), upserts `mirror_entries`, reconciles only when `listing_ok`, and, for automation, creates requests in batches of at most 50 bounded by `max_requests_per_run` (default 50) and `max_open_requests`. It never fetches book bodies.
- The incomplete-book recheck is the same sequence with kind `incomplete`. Automation is off by default.

## Publish hand-off to catalog

1. `publish` runs only when `build_artifacts.state = 'built'` (the audit passed).
2. `POST catalog /internal/books/{book_id}/versions` (metadata, EPUB, cover, preview) with `Idempotency-Key = build_hash` and the internal service token. A replay returns the same version (README OPEN-5: ingestion chooses `book_id`).
3. 200/201 sets the artifact `sent`, stores `version_id` and sets the request `done` / `published` (the version is already visible; no human step, D-49). A 5xx or timeout is retryable; a 4xx is permanent (`catalog_rejected`, review item).
4. Catalog publishes the version in the same call (no approval, D-49). Ingestion pulls catalog events (`GET /internal/events?after=<cursor>`, cursor in `event_cursors`, idempotent by `version_id`), and also resyncs through `GET /internal/books` if the cursor is lost. `book.published` sets the artifact `accepted` (confirmation). A build with any failed gate never reaches catalog and nothing is visible to readers (INV-ING-036).
5. The files of the previous published version are kept until the next version is published.

## Review and reprocessing

- Review inbox: `review_items` by kind with evidence and typed resolution actions; `duplicate_reviews` are separate. A resolution is stored as an override input and replayed by every later run, so a reprocess never undoes a curator decision.
- Reprocess: run curate and duplicate_check on the stored scrape cache with a chosen ruleset version without publishing, show a structured diff (sections, entities, text), and only on explicit apply run build and publish as a new version. The previous published version stays until the new one is published. Re-anchoring annotations is a reader concern.

## Retention job

Daily `retention` job (idempotent): raw scraped pages at 30 days, files of terminal requests, expired `job_log` and `events` rows, superseded candidate files. It never touches files of the currently published version or the previous version before the next one is published ([domain model](../domain-model.md) section 11).

## Failure handling

| Failure | Handling |
|---|---|
| Source 5xx or timeouts | retryable with back-off; after the attempts the request is `needs_review` (`IncompleteSource`), not silently failed |
| Source outage or bot block that persists | no evasion; the operator is shown the cause (credential status, `source_changed`, block page) |
| 401/403/login page, expired cookie | `auth_required`; `awaiting_credential`; the credential status is shown on every console screen |
| Parse yields zero blocks | `needs_review` (`ConservationFailure` or `LockedSource`) |
| Validator invariant false | `needs_review (ConservationFailure)`; `invariant_violation` metric |
| Build audit fails | artifact `audit_failed`, `needs_review (BuildFailed)`; retry allowed; nothing sent |
| Catalog unavailable | retryable; idempotent publish; no duplicate version |
| Worker kill | lease expiry requeues; outputs recomputed or reused by key |
| Source layout changed | `SourceDrift` review; new scrape jobs of that adapter held until the canary passes |

## Observability

Structured logs carry the job correlation id; per job: step timings, block counts per stage, ledger summary, review counts; per ruleset: gold metrics. Queue depth, oldest queued age, lease-expiry count, credential status and drift state are exported. The console receives `request.changed` and `job.progress` through SSE; GET endpoints remain the record.
