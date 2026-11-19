# ADR-0013 — Legacy migration: offline ETL, parallel run, single cutover

Status: REVIEW

## Context
The failed branch changed schemas in place. Production data must survive.

## Decision
Legacy stays untouched and read-only after a freeze. A repeatable ETL (idempotent steps keyed by legacy IDs) loads each new service database; a reconciliation report compares counts, checksums and sampled records. Rehearse on staging until diff is empty. Cutover: freeze legacy writes → final ETL → verification → DNS/proxy switch; rollback = switch back (legacy untouched). Published artifacts are *rebuilt* from migrated canonical documents where available; otherwise legacy EPUBs are imported as-is and flagged `legacy_build`.

## Consequences
+ No in-place risk; rollback is trivial until the legacy system is decommissioned.
− Writes during the freeze window are unavailable (announced; minutes).
