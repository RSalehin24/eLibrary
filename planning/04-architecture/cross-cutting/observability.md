# Observability

Status: DRAFT

## Signals

| Signal | Tooling | Required content |
|---|---|---|
| Logs | `tracing` JSON | `ts`, `level`, `service`, `version`, `request_id`, `subject` (hashed), `route`, `latency_ms`, `error.code`; never secrets |
| Metrics | Prometheus `/metrics` | RED per route; DB pool; outbox depth/age; queue depth/age; job state counts; projection drift; gold-metric gauges; ruleset version |
| Traces | OpenTelemetry | request → service → DB/peer spans |
| Audit | INSERT-only tables | who, what, target, before/after hash, request id |

## SLOs (initial)

| Service | SLI | Objective |
|---|---|---|
| catalog public | availability / p95 latency | 99.5% / 300 ms |
| content (chapters) | availability / p95 TTFB | 99.5% / 400 ms |
| search | p95 latency | 250 ms |
| identity login | availability | 99.5% |
| outbox | oldest pending age | < 60 s p99 |
| ingestion | job success rate (non-source-fault) | ≥ 98% |

## Alerts (page only on user-visible or data-risk)

Error budget burn; outbox oldest age > 5 min; `invariant_violation` > 0; projection drift > 0;
backup older than 26 h; certificate expiry < 14 d; disk > 80%; source canary failing;
ruleset gold regression detected in CI of a release candidate.

## Dashboards

One per service (RED + domain), one "ingestion health" (queue, review backlog, drift), one "platform" (DB, disk, backups).
