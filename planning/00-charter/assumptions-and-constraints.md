# Assumptions and constraints

Status: DRAFT

## Constraints

- **C-1** Backend and shared code are Rust (stable toolchain pinned in `rust-toolchain.toml`).
- **C-2** One developer. Operational surface must stay small: PostgreSQL, an object/file store, a reverse proxy. No broker, no Redis in v1.
- **C-3** Bengali is the primary content language; English is secondary. All text handling must be Unicode-correct.
- **C-4** Existing production data (~1,800 published books, accounts, annotations) must be migrated without loss.
- **C-5** Anonymous visitors may search and preview; reading requires an account.

## Assumptions (each is checked by a spike or decision)

| ID | Assumption | Verified by |
|---|---|---|
| A-1 | The source site keeps its LearnDash structure | Fetch fixtures + canary job; schema drift detector (see ingestion/acquisition) |
| A-2 | We are allowed to ingest and republish the source content as today | Decision D-03 (blocking for ingestion go-live) |
| A-3 | Postgres `FOR UPDATE SKIP LOCKED` queues suffice for ≤ 10 concurrent jobs | Spike S-07 |
| A-4 | A Rust search index can handle Bengali variants well enough | Spike S-01 against the query set |
| A-5 | Bengali glyph shaping for generated covers is solvable in Rust | Spike S-03 |
| A-6 | ~1,800 books × average size fits a single host's storage comfortably | Measured in P0 inventory |
| A-7 | TLA+/Alloy tooling is available in CI (Java) | Spike S-04 |
