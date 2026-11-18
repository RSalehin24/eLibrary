# Orchestration - job queue, leases, scheduling, publish hand-off

Status: DRAFT (rewritten for the PostgreSQL job queue, D-27/D-29; ADR-0021)

How work runs. No saga, no Redis, no broker, no work inside an HTTP request. Tables: [domain model](../domain-model.md) (`jobs`, `requests`, `sync_runs`, `automation_settings`). Transitions: [state machines](../state-machines.md). This page is the operating summary and the failure table.

## Containers

`ingestion-api` serves HTTP and SSE and only inserts rows. `ingestion-worker` (same image, command `worker`) runs the claimer, the executors, the reaper and the scheduler tick.

## Job queue

- A job is a row in `jobs`; the next job of a request is inserted in the same transaction as the previous job's success (scrape, curate, duplicate_check, build, publish). Kinds: those five plus `sync`, `check_credential`, `scheduler_tick`.
- Claim: `UPDATE ... WHERE id = (SELECT ... WHERE state='queued' AND run_after <= now() ORDER BY priority DESC, run_after, id FOR UPDATE SKIP LOCKED LIMIT 1)` sets `state='running'`, `lease_epoch+1`, `lease_expires_at = now()+120 s`, `attempt+1`.
- Lease: heartbeat every 30 s extends `lease_expires_at`. Every executor write carries `AND lease_epoch = $epoch` (fencing); a zombie's writes touch zero rows and it stops.
- Reaper (worker, every 30 s, idempotent): `running` with an expired lease goes back to `queued` (attempt < max) or to `failed` (`lease_expired`). It is the only time-driven transition (INV-ING-010).
- Idempotency: each step is safe to run twice; outputs are keyed by input hashes (page url key, `(request_id, version_no)`, `build_hash`) so a second run is a no-op or writes identical bytes. `jobs.idempotency_key` is unique.
- Concurrency: worker slots from settings (scrape default 2 slots, one in-flight request per source host) with the 0.5 s page delay; priority manual > reprocess > sync > scheduled recheck.

## Typed errors

Executors return `JobError::Retryable{code, retry_after?}` or `JobError::Permanent{code}`; the queue decides only from the class, never from message text.

| Class | Codes (examples) | Effect |
|---|---|---|
| Retryable | `network`, `timeout`, `http_5xx`, `rate_limited`, `catalog_unavailable` | requeue with `run_after = now + base*2^attempt + jitter` while `attempt < max_attempts` (default 3); then failed |
| Permanent | `locked_source`, `source_changed`, `invalid_document`, `build_failed`, `catalog_rejected`, `unsupported` | job failed; request moves to `needs_review` with the matching review item, or `failed` |
| Permanent, resumable | `auth_required` | job failed; request `awaiting_credential`; a new credential requeues it in the same transaction |

A job `succeeded` only means the step ran. The request state carries the outcome, so a failed build can never be reported as success.

## Cancel

The API sets `cancel_requested` on the request and its job. A `queued` job is cancelled at once. A running executor reads the flag before every page and between steps, writes its cursor, and ends as `cancelled`; a single in-flight HTTP request cannot be interrupted (bounded by its timeout). Cancelling a request in `in_catalog_review` is refused: reject the version in catalog.

## Sync and automation scheduling

- `scheduler_tick` (one job, every 60 s, claimed like any job) finds due `automation_settings` rows in one transaction, inserts the `sync_runs` row and its `sync` job, and moves `next_due_at` to the next slot from the injected clock at the same moment. A failure therefore never causes a one-minute retry loop; a slot missed during downtime runs once. Exact sequence: [state machines](../state-machines.md) "Automation sequence".
- The `sync` job pages through the source listing (bounded, checkpointed per page), upserts `mirror_entries`, reconciles only when `listing_ok`, and (automation only) creates requests in batches of at most 50, bounded by `max_requests_per_run` (default 50) and `max_open_requests` (back-pressure; the job requeues itself after 60 s). It never fetches book bodies.
- Incomplete-book recheck is the same sequence with kind `incomplete`.
- Automation is off by default; mode `pending` selects never-requested entries only.

## Publish hand-off to catalog

1. `publish` runs only when `build_artifacts.state = 'built'` (the audit passed).
2. `PUT catalog /internal/books/by-source/{key}` finds or creates the invisible book shell; then `POST catalog /internal/books/{id}/versions` (multipart: metadata, EPUB, cover, preview) with `Idempotency-Key = build_hash` and the internal service token. A replay returns the same version.
3. 201/200 sets the artifact `sent` and the request `in_catalog_review`. 5xx/timeout is retryable; 4xx is permanent (`catalog_rejected`, review item).
4. Catalog makes the version `in_review`; a holder of `manage_catalog` approves. Ingestion pulls catalog `GET /internal/events?after=<cursor>` (cursor in `event_cursors`, idempotent by `version_id`): `book.published` sets the request `published` and the artifact `accepted`; a rejection in `book.version_changed` sets `needs_review (CatalogRejected)`. Nothing is visible to readers before approval, and a failed build never reaches catalog.
5. Files of the previous published version are kept until the next version is approved (retention default).

## Review and reprocessing

- Review inbox: `review_items` by kind with evidence and typed resolution actions; `duplicate_reviews` are separate. A resolution is stored as an override input and replayed by every later run, so a reprocess never undoes a curator decision.
- Reprocess: select requests and a ruleset version, run curate and duplicate_check on the stored scrape cache without publishing, show a document diff (section tree, entities, text counts), and only on explicit apply run build and publish with a new version. The previous published version stays until the new one is approved. Annotation re-anchoring is a reader concern and is not computed here.

## Failure handling

| Failure | Handling |
|---|---|
| Source 5xx/timeouts | retryable with backoff; after the attempts: request `needs_review` (`IncompleteSource`), not silently failed |
| 401/403/login page, expired cookie | `auth_required`; request `awaiting_credential`; credential status shown on every console screen |
| Parse yields zero blocks | `needs_review` (`ConservationFailure` or `LockedSource`) |
| Validator invariant false | `needs_review (ConservationFailure)`; `invariant_violation` metric |
| Build audit fails | artifact `audit_failed`, `needs_review (BuildFailed)`; retry allowed; nothing sent |
| Catalog unavailable | retryable; idempotent publish; no duplicate version |
| Worker crash | lease expiry requeues; outputs recomputed or reused by key |
| Source layout changed | `SourceDrift` review; new scrape jobs of that adapter held, canary decides |

## Observability

Per job: step timings, block counts per stage, conservation ledger summary, review counts. Per ruleset: gold metrics. Queue depth and oldest queued age, lease-expiry count, credential status and drift state are exported (small scale: logs and metrics only). The console receives `request.changed` and `job.progress` through SSE; GET endpoints remain the record.
