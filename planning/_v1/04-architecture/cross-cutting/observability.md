# Observability

Status: DRAFT

## Signals

| Signal | Tooling | Required content |
|---|---|---|
| Logs | `tracing` JSON | `ts`, `level`, `service`, `version`, `request_id`, `subject` (hashed), `route`, `latency_ms`, `error.code`; never secrets |
| Metrics | Prometheus `/metrics` | RED per route; DB pool; event cursor lag; job queue depth/age; job state counts; copy drift (reader copies vs catalog versions); gold-metric gauges; ruleset version |
| Traces | OpenTelemetry | request → service → DB/peer spans |
| Audit | INSERT-only tables | who, what, target, before/after hash, request id; reader records every book open |

## SLOs (initial)

| Service | SLI | Objective |
|---|---|---|
| catalog public | availability / p95 latency | 99.5% / 300 ms |
| reader (whole-book response) | availability / p95 TTFB | 99.5% / 800 ms |
| catalog search (PostgreSQL FTS) | p95 latency | 250 ms |
| identity login | availability | 99.5% |
| events | consumer cursor lag | < 60 s p99 |
| ingestion | job success rate (non-source-fault) | ≥ 98% |

## Alerts (page only on user-visible or data-risk)

Error budget burn; event cursor lag > 5 min; `invariant_violation` > 0; reader copy drift > 0; job lease expiries rising;
backup older than 26 h; certificate expiry < 14 d; disk > 80%; source canary failing;
ruleset gold regression detected in CI of a release candidate.

## Dashboards

One per service (RED + domain), one "ingestion health" (job queue, review backlog, source cookie status, drift), one "platform" (DB, disk, backups).
