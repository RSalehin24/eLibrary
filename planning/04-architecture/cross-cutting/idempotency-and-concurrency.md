# Idempotency and concurrency

Status: DRAFT

## Idempotency

| Mutation kind | Mechanism |
|---|---|
| Create with natural key (book from source URL, shelf entry, grant) | `UNIQUE` on the natural key; `INSERT … ON CONFLICT` returns the existing row |
| Create without natural key | Client supplies `Idempotency-Key` (UUID); table `idempotency(key, route, request_hash, response, expires)` written in the same transaction; same key + different hash → 422 `idempotency_conflict` |
| Event consumption | `(consumer, event_id)` unique row in the same transaction as the effect |
| Job steps | `(job_id, step, epoch)` key; step results are stored and reused |
| External side effects (mail) | Provider-side idempotency token where available; otherwise at-least-once is recorded and bounded to one per `(event_id, kind)` by a *claim-before-send* row |

## Concurrency control

- **Optimistic**: aggregates carry `revision`; updates `WHERE id=$1 AND revision=$2`; zero rows → `409 stale_revision` (client reloads; never auto-merge).
- **Claims**: `UPDATE … WHERE id IN (SELECT … FOR UPDATE SKIP LOCKED LIMIT n)` with lease expiry and epoch.
- **Exclusion**: PostgreSQL `EXCLUDE` or partial unique indexes for "≤ 1 active X per Y" (e.g. one active job per source URL).
- **Isolation**: default READ COMMITTED; use SERIALIZABLE (with retry on 40001) only for read-once opening consumption and grant revocation vs. decision races.

## Ordering

Per-aggregate ordering by `(subject_id, sequence)` on events; consumers detect gaps
and request a resync of that aggregate instead of guessing.
