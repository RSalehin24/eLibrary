# Non-functional targets

Status: DRAFT

Targets live in one place; requirements and gates refer here. (Numeric limits: [limits](../04-architecture/cross-cutting/limits.md); performance scenarios: [performance](../09-testing/performance.md).)

| Quality | Target | Where verified |
|---|---|---|
| Availability (public read) | 99.5% monthly | SLO dashboards ([observability](../04-architecture/cross-cutting/observability.md)) |
| Latency | search p95 ≤ 250 ms; book page p95 ≤ 300 ms; chapter p95 ≤ 400 ms | load tests |
| Recovery | RPO ≤ 15 min, RTO ≤ 1 h | restore drill |
| Security | all threat-model items mitigated or accepted in writing | [threat model](../10-security/threat-model.md) |
| Accessibility | WCAG 2.2 AA | a11y scans + manual |
| Browser support | last 2 versions of Chromium, Firefox, Safari; Android Chrome; iOS Safari ≥ 16 | e2e matrix |
| Internationalization | bn + en complete; no hardcoded strings | catalog parity test |
| Maintainability | no service→service crate dependency; each service buildable and testable alone | Q6 |
| Determinism | builds and pipeline stages deterministic | gold + prop tests |
| Observability | RED + domain metrics per service; request ids everywhere | e2e |
| Data integrity | zero unexplained migration differences; projection drift = 0 | reconciliation |
| Capacity | 2,000 books, 50 rps public, 10 concurrent ingestion jobs on one host | load tests |
