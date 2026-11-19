# Platform and non-functional ownership

Status: DRAFT

Who implements each cross-cutting requirement, and which document tests it. "All" means every Rust service (gateway, identity, catalog, reader, ingestion, notify) through the shared workspace crates described in [workspace layout](workspace-layout.md); infrastructure means the Compose files, `caddy`, `postgres`, `migrate` and `backup` ([deployment topology](deployment-topology.md)). Service-level `TST-*` rows live in each `05-services/*/test-plan.md`; this table only names the owning document.

Test documents: [strategy](../09-testing/strategy.md) (S), [fault injection](../09-testing/fault-injection.md) (FI), [performance](../09-testing/performance.md) (P), [quality gates](../03-correctness/quality-gates.md) (QG), [environments and CI](../11-operations/environments-and-ci.md) (CI), [backup and restore](../11-operations/backup-restore.md) (BR), [secrets and keys](../10-security/secrets-and-keys.md) (SK), [threat model](../10-security/threat-model.md) (TM).

## Platform requirements

| Requirement | Implemented by | Tested in |
|---|---|---|
| REQ-PLT-001 Docker Compose, one container per component | infrastructure | CI, QG (Q11), S |
| REQ-PLT-002 database and role per service | infrastructure (`migrate`), all services | QG (Q11), service test plans |
| REQ-PLT-003 startup validation of configuration and schema version | all ([config and startup](cross-cutting/config-and-startup.md)) | S, service test plans |
| REQ-PLT-004 liveness and readiness endpoints | all | TST-GWY-018 and the other service plans, FI |
| REQ-PLT-005 generated contract types | all, web (`xtask codegen`) | S (contract checks), CI |
| REQ-PLT-006 idempotent mutations | all ([idempotency](cross-cutting/idempotency-and-concurrency.md)) | service test plans, S (property tests) |
| REQ-PLT-007 no reachable panic, fuzzed parsers | all | QG, S (fuzz targets), TST-GWY-006, TST-IDN-042 |
| REQ-PLT-008 explicit bounds | all ([limits](cross-cutting/limits.md)) | service test plans, P, FI-17 |
| REQ-PLT-009 audit of security and admin actions | identity, catalog, reader, ingestion | TST-IDN-035, TST-CAT-031, TST-RDR-012, TST-ING-037 |
| REQ-PLT-010 same-transaction outbox, pull events | identity, catalog, ingestion (producers); reader, notify, ingestion (consumers) | TST-IDN-031, TST-CAT-024, TST-RDR-026, TST-ING-005, FI-12 |
| REQ-PLT-011 injected `Clock`, UTC | all ([text and time](cross-cutting/text-and-time.md)) | QG, FI-18 |
| REQ-PLT-012 size and shape rules | all | QG (Q1) |
| REQ-PLT-013 dependency approval | all | QG, [dependency policy](dependency-policy.md), CI |
| REQ-PLT-014 no weakened lints, waivers dated | all | QG, [waivers](../12-roadmap/waivers.md) |
| REQ-PLT-015 automated backups | infrastructure (`backup`) | BR, FI-19, restore drill |
| REQ-PLT-016 secrets as read-only files (full inventory) | infrastructure, all services (loaders), `caddy` (certificates) | SK, TM (T-17), QG |
| REQ-PLT-017 no pipeline work inside a request | ingestion, notify, catalog | TST-ING-006, FI-06 |
| REQ-PLT-018 typed errors and one envelope | all ([errors](cross-cutting/errors.md)) | TST-ING-007, service test plans |
| REQ-PLT-019 structured logs, RED metrics, alerts | all, infrastructure ([observability](cross-cutting/observability.md)) | S, FI, CI |
| REQ-PLT-020 internal service tokens | all ([service auth](cross-cutting/service-auth.md)) | service test plans, TM |
| REQ-PLT-021 bounded retention jobs | identity, catalog, reader, ingestion, notify | TST-ING-036, service test plans |
| REQ-PLT-022 rolling release with rollback | infrastructure | FI, CI, [runbooks](../11-operations/runbooks/README.md) |
| REQ-PLT-023 one source of truth for state | all (database constraints) | service test plans, QG (Q11) |

## Non-functional requirements

| Requirement | Implemented by | Tested in |
|---|---|---|
| REQ-NFR-001 availability 99.5% | infrastructure, gateway | P, G9 observation ([gates](../12-roadmap/gates.md)) |
| REQ-NFR-002 latency at 50 users | gateway, identity, catalog, reader | P |
| REQ-NFR-003 capacity | all | P |
| REQ-NFR-004 recovery (RPO 30 days, RTO 4 h) | infrastructure (`backup`) | BR, FI-19 |
| REQ-NFR-005 memory and image size | infrastructure, all | P, CI |
| REQ-NFR-006 payload and page limits | gateway, catalog, identity | TST-GWY-013, TST-CAT-027, TST-IDN-041, FI-17 |
| REQ-NFR-007 security baseline | gateway, identity, infrastructure | TM, [abuse and privacy](../10-security/abuse-and-privacy.md), QG |
| REQ-NFR-008 accessibility | web | S (web rows, axe), TST-RDR-022 |
| REQ-NFR-009 browser and window support | web | S (Playwright matrix) |
| REQ-NFR-010 internationalization | web, catalog, notify | S (web rows), TST-CAT-010 |
| REQ-NFR-011 independent builds | workspace | QG, CI |
| REQ-NFR-012 determinism | ingestion, reader | TST-ING-014, TST-ING-015, TST-RDR-002 |
| REQ-NFR-013 projection drift zero | catalog, reader, ingestion | FI-12, TST-RDR-026, TST-CAT-037 |
| REQ-NFR-014 startup and restart time | infrastructure, all | P, FI-20 |
