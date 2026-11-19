# ADR-0002 — Independent services, modular deployment

Status: SUPERSEDED

Superseded by [ADR-0025](0025-six-services-with-gateway.md) (six services including a gateway, D-31); [ADR-0020](0020-five-services-no-gateway.md) was an intermediate step. The seven-service split below is historical.

## Context
Complexity and thinking scope per feature must shrink. The legacy monolith had import cycles and a shared database. The rewrite branch kept a monolith and added more frameworks.

## Decision
Seven domain services plus gateway and web ([catalog](../service-catalog.md)). Each is its own crate/binary, its own Docker container (ADR-0019) and its own database. Services depend only on contracts. For local development, `xtask dev` runs all services in one process; production runs them as separate processes on one host initially.

## Consequences
+ A feature touches one service; others are mocked through contracts.
+ Failure isolation (ingestion cannot take down browsing).
− Distributed failure modes (partial failure, version skew). Mitigated by the outbox, idempotency, contract handshake, saga with compensation and the [formal models](../../03-correctness/formal-models/README.md).
− More operational surface. Mitigation: consolidation escape hatch (co-deploy identity+access+notify) without code change.
