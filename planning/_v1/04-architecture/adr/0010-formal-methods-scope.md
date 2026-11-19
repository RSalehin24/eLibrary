# ADR-0010 — Formal methods: scope and limits

Status: REVIEW

## Context
The owner wants confidence that design-phase errors are eliminated. Full program verification of the system is unrealistic; targeted use is realistic.

## Decision
Use TLA+ for state machines and protocols (job lifecycle, read-once, outbox, account lifecycle, publication, progress), Alloy for the authorization policy, `kani`/`proptest` for small pure cores, and model-based tests tying Rust code to the TLA+ traces. Everything else relies on types, DB constraints, and corpus measurement ([verification ladder](../../03-correctness/verification-ladder.md)).

## Consequences
+ The riskiest concurrent and security logic is checked exhaustively within stated bounds.
− Needs Java for TLC/Alloy in CI (spike S-04); models need upkeep (rule: change model and invariant together).
