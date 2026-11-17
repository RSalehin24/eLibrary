# ADR-0005 — Postgres-backed outbox and job queues, no broker

Status: REVIEW

## Context
Legacy used Celery + Redis; the rewrite branch added RabbitMQ and ended with hundreds of thousands of unconsumed envelopes. One developer should not operate a broker.

## Decision
Events use a transactional outbox per service with an HTTP relay to subscribers; durable jobs use a `jobs` table claimed with `FOR UPDATE SKIP LOCKED`, leases and fencing epochs ([JobLifecycle](../../03-correctness/formal-models/tla/JobLifecycle.tla)). A broker can be introduced later behind the `platform-db` queue/outbox interfaces. Spike S-07 confirms throughput.

## Consequences
+ Atomic state+event; fewer moving parts; easy to inspect and replay.
− Polling latency (target ≤ 1 s via `LISTEN/NOTIFY` wakeups); throughput ceiling (adequate for ≤ 10 concurrent jobs).
