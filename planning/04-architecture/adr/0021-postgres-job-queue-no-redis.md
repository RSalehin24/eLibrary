# ADR-0021 — PostgreSQL job queue, no Redis, no Celery

Status: ACCEPTED

Supersedes the job-queue part of [ADR-0005](0005-postgres-outbox-and-queues.md). Basis: D-27, D-29, D-31.

## Context
The legacy system ran a job engine over Redis pub/sub and Celery: messages were lost, jobs ran twice, failures were reported as success, and the pipeline ran inside the HTTP request when dispatch failed. At under 5,000 books and a handful of concurrent jobs, no broker is justified.

## Decision
- Durable work is rows in a `jobs` table in the ingestion database. Workers claim rows with `FOR UPDATE SKIP LOCKED`, hold a lease renewed by heartbeat, and lose it after a visibility timeout; each row has an attempt counter.
- Outcomes are typed: `retryable` (re-queued with back-off) or `permanent` (terminal, shown on the console). Retry is never decided from error text.
- Steps are idempotent, keyed by `(job_id, step)`. Cancellation is a flag checked cooperatively per page.
- No work runs inside an HTTP request or in the API container; the `ingestion-worker` container (same image as `ingestion-api`, different command) is the only executor.
- Wake-ups use `LISTEN/NOTIFY` with a polling fallback; correctness never depends on the notification.
- There is no Redis, Celery or message broker in the stack. Console live updates are Server-Sent Events fed from an outbox with a versioned snapshot on reconnect.

## Consequences
+ State and queue commit atomically; the queue is inspectable with SQL; one fewer stateful container to back up.
+ Lost messages and double runs are excluded by leases and idempotent steps (model: [JobLifecycle](../../03-correctness/formal-models/tla/JobLifecycle.tla)).
- Throughput is bounded by PostgreSQL polling (ample at this scale); a broker is not planned and would need a new ADR.
