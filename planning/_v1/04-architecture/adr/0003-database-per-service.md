# ADR-0003 — PostgreSQL database per service

Status: REVIEW

## Context
Shared tables and foreign keys across apps created the legacy coupling.

## Decision
One PostgreSQL server (v1; a single container, ADR-0019/D-24), one database and one login role per service. No cross-database access. `sqlx` compile-time query checking against each service's migrated schema. Forward-only migrations with expand/contract.

## Consequences
+ Ownership enforced by credentials, not by convention.
+ Independent schema evolution.
− No cross-service joins; projections and reconciliation jobs are needed ([data ownership](../data-ownership.md)).
