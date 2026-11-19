# Idempotency and concurrency

Status: DRAFT

## Idempotency

| Mutation kind | Mechanism |
|---|---|
| Create with natural key (request from source URL, shelf entry, saved filter, grant) | `UNIQUE` on the natural key; `INSERT … ON CONFLICT` returns the existing row |
| Create without natural key | Client supplies `Idempotency-Key` (UUID); table `idempotency(key, route, request_hash, response, expires)` written in the same transaction; same key + different hash → 422 `idempotency_conflict` |
| Internal publish (ingestion to catalog) | Build identity `(book_id, build_hash)` is unique; a retry returns the existing (already published) version |
| Reading ticket redemption | Same ticket redeemed twice is the same opening; read-once counter moves once |
| Event consumption | Idempotent effect; the consumer's cursor advances in the same transaction as the effect (pull-based events, [ADR-0022](../adr/0022-pull-based-outbox-events.md)) |
| Job steps | `(job_id, step)` key; step results are stored and reused; a retried attempt skips completed steps |
| External side effects (mail) | Provider-side idempotency token where available; otherwise at-least-once is recorded and bounded to one per `(event_id, kind)` by a *claim-before-send* row in notify |

## Concurrency control

- **Optimistic**: aggregates carry `revision`; updates `WHERE id=$1 AND revision=$2`; zero rows → `409 stale_revision` (client reloads; never auto-merge).
- **Claims**: `UPDATE … WHERE id IN (SELECT … FOR UPDATE SKIP LOCKED LIMIT n)` with a heartbeat-renewed lease, visibility timeout and attempt counter ([ADR-0021](../adr/0021-postgres-job-queue-no-redis.md)).
- **Exclusion**: PostgreSQL `EXCLUDE` or partial unique indexes for "≤ 1 active X per Y" (e.g. one active job per source URL).
- **Isolation**: default READ COMMITTED; use SERIALIZABLE (with retry on 40001) only for read-once consumption (ticket redemption in identity) and grant revocation vs. decision races.
- **Progress**: reader progress carries a strictly increasing `revision`; a stale write is a no-op returning the stored value.

## Ordering

Events are ordered by the producer's monotonic `cursor`; consumers detect a lost cursor
and resynchronize from the owner's listing endpoint instead of guessing.
