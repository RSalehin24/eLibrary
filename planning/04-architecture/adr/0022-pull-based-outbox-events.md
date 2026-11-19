# ADR-0022 — Pull-based outbox events

Status: ACCEPTED

Supersedes the event-delivery part of [ADR-0005](0005-postgres-outbox-and-queues.md) (the HTTP push relay and subscriber inbox endpoints). Basis: D-27, D-31 (the gateway neither produces nor consumes events).

## Context
The earlier design pushed outbox rows to subscribers' inbox endpoints, which needs a relay, subscriber registration, per-consumer dedupe tables and retry state on the producer. With six services and few consumers a simpler pull model suffices.

## Decision
- A producer writes an `events` row (monotonic cursor, type, version, payload of ids and minimum data) in the same transaction as the change, and exposes `GET /internal/events?after=<cursor>` (service token required).
- A consumer stores its own cursor, pulls in batches, applies each event idempotently, and advances the cursor in the same transaction as the effect. It tolerates duplicates, restarts and gaps in time.
- Events: `book.published`, `book.unpublished`, `book.version_changed` (catalog to reader and ingestion); `user.disabled`, `grant.changed` (identity to reader and to catalog caches); `email.requested`, `kindle.requested` (identity and catalog to notify); `build.finished` (ingestion internal).
- Events are an optimization and a trigger, never the only source of truth: a consumer that is far behind or loses its cursor can resynchronize from the owner's listing endpoint.
- Retention: events older than the retention horizon (set in [limits](../cross-cutting/limits.md)) are pruned only after every known consumer cursor has passed them.

## Consequences
+ No relay process, no subscriber registry; producers are stateless towards consumers; replay is "reset the cursor".
- Latency is the polling interval (target at most a few seconds; `LISTEN/NOTIFY` may shorten it); a stalled consumer blocks pruning (alert on cursor lag).
- Ordering is by cursor within one producer only.

Model: [Outbox](../../03-correctness/formal-models/tla/Outbox.tla) (to be adapted to pull semantics by the correctness stage).
