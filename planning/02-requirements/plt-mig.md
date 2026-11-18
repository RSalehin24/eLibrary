# Requirements — Platform (PLT) and Migration (MIG)

Status: DRAFT

## Platform — cross-cutting, see [cross-cutting designs](../04-architecture/cross-cutting/)

- **REQ-PLT-001** · MUST · inv: INV-PLT-001 · verify: e2e, unit · A service starts only if its configuration validates, its database schema version matches the binary, and peer contract versions are compatible; otherwise it exits with a typed error.
- **REQ-PLT-002** · MUST · inv: INV-PLT-002 · verify: type, e2e · Every cross-service call and event uses types generated from the contract crates. Breaking changes require a version bump and a passing compatibility test.
- **REQ-PLT-003** · MUST · inv: INV-PLT-003 · verify: prop · Every mutating endpoint is idempotent (natural key or `Idempotency-Key`); replay returns the original result.
- **REQ-PLT-004** · MUST · inv: INV-PLT-004 · verify: fuzz, unit · No panic is reachable from request handling: `unwrap`/`expect`/indexing are denied by lint outside tests; parsers are fuzzed.
- **REQ-PLT-005** · MUST · inv: INV-PLT-005 · verify: prop, e2e · Every queue, list, body, timeout, retry and concurrency has an explicit documented bound ([limits](../04-architecture/cross-cutting/limits.md)).
- **REQ-PLT-006** · MUST · inv: INV-PLT-006 · verify: db, e2e · Security- and admin-relevant actions append to an audit log that no service role can update or delete.
- **REQ-PLT-007** · MUST · inv: INV-PLT-007 · verify: e2e · Logs, metrics and traces carry request id and service version; SLO dashboards and alerts exist per service.
- **REQ-PLT-008** · MUST · inv: INV-PLT-008 · verify: drill · Backups are automated and a restore drill (database + artifacts) passes quarterly within RTO.
- **REQ-PLT-009** · MUST · inv: INV-PLT-009 · verify: model, prop · State change and event publication happen in one transaction (outbox); consumers are idempotent; no event is lost or applied twice.
- **REQ-PLT-010** · MUST · inv: INV-PLT-010 · verify: type, unit · Time is injected through a `Clock` trait; all stored times are UTC; the UI displays in the viewer's zone (default Asia/Dhaka).

- **REQ-PLT-011** · MUST · inv: INV-PLT-011 · verify: type, review · Code obeys the owner's size and shape rules: functions ~20 lines (cap 30), at most 3 parameters (group inputs in a struct), at most 2 nesting levels, no boolean flag parameters, no magic numbers; thresholds are lint-enforced where the tool supports it and checked in review otherwise ([coding standards](../03-correctness/coding-standards.md)).
- **REQ-PLT-012** · MUST · inv: INV-PLT-012 · verify: review, drill · No dependency (crate, tool or system package) is added without the owner's recorded approval; the standard library is preferred; the approved register matches the lockfile ([dependency policy](../04-architecture/dependency-policy.md)).
- **REQ-PLT-013** · SHOULD · inv: INV-PLT-013 · verify: type · Public items of `contracts-*` and `domain-*` crates are documented (lint-enforced) and doctests run in CI.
- **REQ-PLT-014** · MUST · inv: INV-PLT-014 · verify: e2e, review · The whole system is built, run and deployed with Docker Compose, one container per component ([topology](../04-architecture/deployment-topology.md)); the same images run in dev, CI, staging and production; only `edge` publishes host ports; each service reaches only its own database.

## Migration

- **REQ-MIG-001** · MUST · inv: INV-MIG-001 · verify: drill · Legacy data is migrated by repeatable, idempotent steps and a reconciliation report shows counts, checksums and per-entity mappings with zero unexplained differences.
- **REQ-MIG-002** · MUST · inv: INV-MIG-002 · verify: e2e · Legacy book URLs (slug/code) resolve in the new system directly or by permanent redirect.
- **REQ-MIG-003** · MUST · inv: INV-MIG-003 · verify: unit, e2e · Legacy Django password hashes verify and are re-hashed to Argon2id on next successful login.
- **REQ-MIG-004** · MUST · inv: INV-MIG-004 · verify: drill · Until the cutover gate, a tested rollback restores the legacy system as primary without data loss.
