# Observability

Status: DRAFT

## Signals

| Signal | Tooling | Required content |
|---|---|---|
| Logs | `tracing` JSON | `ts`, `level`, `service`, `version`, `request_id`, `subject` (hashed), `route`, `latency_ms`, `error.code`; never secrets |
| Metrics | Prometheus `/metrics` | RED per route; DB pool; event cursor lag; job queue depth/age; job state counts; copy drift (reader copies vs catalog versions); notify outbox depth; source credential days left; gold-metric gauges; ruleset version |
| Traces | OpenTelemetry | request → service → DB/peer spans |
| Audit | INSERT-only tables, 1 year (D-40) | who, what, target, before/after hash, request id; identity records ticket mint and redemption, reader records every book open, catalog records downloads and publish actions |

## SLOs (initial)

| Service | SLI | Objective |
|---|---|---|
| gateway plus identity authorize overhead | p95 | 25 ms |
| catalog public | availability / p95 latency | 99.5% / 300 ms |
| reader open (ticket) / whole-book package (up to 5 MB) | p95 | 300 ms / 1.5 s (provisional, O-7) |
| catalog search (PostgreSQL FTS) | p95 latency | 250 ms |
| identity login | availability | 99.5% |
| events | consumer cursor lag | < 60 s p99 |
| ingestion | job success rate (non-source-fault) | ≥ 98% |

## Alerts (page only on user-visible or data-risk)

Error budget burn; event cursor lag > 5 min; `invariant_violation` > 0; reader copy drift > 0; job lease expiries rising;
backup older than 35 d (monthly, D-33); source credential expiring or expired; certificate expiry < 14 d; disk > 80%; source canary failing;
ruleset gold regression detected in CI of a release candidate.

## Dashboards

One per service including the gateway (RED + domain), one "ingestion health" (job queue, review backlog, source cookie status, drift), one "platform" (DB, disk, backups).
