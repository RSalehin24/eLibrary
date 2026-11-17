# Coding standards (Rust and supporting practices)

Status: DRAFT

Complements [type-driven design](type-driven-design.md) (error elimination) and the [engineering philosophy](../00-charter/engineering-philosophy.md) (rules). Items marked **verify** must be confirmed against the installed tool's documentation before being relied on (we do not invent flags).

## 1. Function and module shape

| Rule | Limit | Enforcement (candidate, verify at G1) |
|---|---|---|
| Function length | ~20 lines (hard cap 30) | clippy `too_many_lines` + `too-many-lines-threshold` in `clippy.toml` |
| Parameters | ≤ 3 | clippy `too_many_arguments` + `too-many-arguments-threshold = 3` |
| Nesting | ≤ 2 levels of control flow | clippy `excessive_nesting` (+ `excessive-nesting-threshold`) and `cognitive_complexity`; review |
| Module size | ≤ ~300 lines; one concept per module | review; size check script |
| File per crate responsibility | `lib.rs` re-exports only | review |

Techniques: early return, `?`, `let … else`, iterator chains, small helper functions with intention-revealing names, parameter structs, enums instead of bool flags.

## 2. Naming and style

Rust API Guidelines naming (RFC 430): `snake_case` fns/vars, `CamelCase` types, `SCREAMING_SNAKE_CASE` consts; conversions `as_`/`to_`/`into_`; getters without `get_`; no abbreviations (`account`, not `acct`); booleans read as predicates (`is_active`). Format with `rustfmt` (default config, checked in CI). Lint with `clippy` (`-D warnings`) with the deny set below.

## 3. Lints (workspace `Cargo.toml` `[workspace.lints]` — verify syntax at G1)

- deny: `unsafe_code` (forbid outside listed crates), `unwrap_used`, `expect_used`, `panic`, `indexing_slicing`, `todo`, `unimplemented`, `dbg_macro`, `print_stdout/stderr` (use tracing), `wildcard_enum_match_arm`, `missing_docs` on `contracts-*` and `domain-*`.
- warn → deny in CI: a curated subset of `clippy::pedantic` (`must_use_candidate`, `needless_pass_by_value`, `module_name_repetitions` allowed explicitly with a reason).
- Every `#[allow(...)]` carries a one-line `// why:` comment and is listed in review; blanket `#![allow]` is forbidden (integrity rule: do not weaken lints).

## 4. API design (library crates)

Follow the Rust API Guidelines checklist: small public surface (`pub(crate)` by default), `#[non_exhaustive]` on public enums/structs in `contracts-*` that may grow, `#[must_use]` on results and builders, constructors validate (`TryFrom`/`parse`), implement standard traits (`Debug`, `Clone`, `PartialEq`, `Eq`, `Hash` where valid; never `Debug` for secrets), `Display` only for user-meaningful text, no public fields on invariant-carrying types, iterators over `Vec` returns where lazy is natural, rustdoc with examples that run as doctests.

## 5. Errors

Closed enums per crate (`thiserror` if approved; otherwise hand-written `impl Error`); `?` + explicit `From`; no `unwrap`/`expect` in non-test code; errors carry context fields, not formatted strings; map to HTTP in one exhaustive function. Panics are bugs: caught at the process boundary only to log and abort the request, with an alert.

## 6. Concurrency and async

- No blocking calls in async tasks (`spawn_blocking` for CPU/IO-heavy sync work, e.g. EPUB building, hashing); CPU-bound pure work runs on a bounded blocking pool.
- Every `await` on external I/O has a timeout; every channel/queue is bounded; backpressure over unbounded buffering.
- Cancellation safety documented for functions used in `select!`; no holding locks across `.await`; prefer message passing/ownership over shared mutable state; `Arc<Mutex<_>>` needs a justification.
- Graceful shutdown: stop accepting, drain in-flight, release leases.
- Data races are impossible in safe Rust; logic races are handled by DB constraints and the models ([idempotency](../04-architecture/cross-cutting/idempotency-and-concurrency.md)).

## 7. Persistence (SQL)

Forward-only migrations (never edit applied ones); explicit column lists; transactions scoped small and short; constraints in the schema, not only code; indexes justified by a query (with `EXPLAIN` in review for hot paths); no N+1 (batch/JOIN within the service); parameterized queries only (sqlx macros); timestamps `timestamptz` UTC; soft delete only where the domain needs history.

## 8. Testing practices

FIRST (fast, independent, repeatable, self-validating, timely); Arrange-Act-Assert; one behavior per test; names state behavior (`denies_read_when_grant_expired`); tests deterministic (injected clock/rng, fixed seeds recorded); property tests for invariants, examples for regressions; no sleeping; no network; no shared state between tests; test the public behavior, not private structure; mutation testing on pure cores ([strategy](../09-testing/strategy.md)).

## 9. Documentation

Public items documented (`missing_docs` deny on domain/contract crates); module-level docs state purpose and invariants; comments explain *why*; ADR for each significant decision; README per crate (purpose, how to test); `CHANGELOG` for contract crates; docs updated in the same change as the code.

## 10. Observability practice

Log at boundaries only (request in/out, job step, external call, state transition), structured, with ids, no secrets and no personal data beyond hashed ids; errors logged once where handled; metrics for rates/latency/saturation; no log-and-rethrow duplication.

## 11. Security practice

Map to OWASP ASVS level 2 for web/API controls (checklist in the threat model review); validate at the edge; output-encode; least privilege; dependency scanning (`cargo audit`, `cargo deny`); secrets only via files with strict permissions; constant-time comparison for secrets; rate limits; CSP.

## 12. Performance practice

**No optimization without evidence.** Budgets in [performance](../09-testing/performance.md); measure first (criterion benchmarks for pure hot paths, k6 for services, flamegraphs); record before/after in the pull request; keep readable code unless a measured budget fails.

## 13. Dependency practice

[Dependency policy](../04-architecture/dependency-policy.md): standard library first; each crate approved by the owner and recorded; pinned via lockfile; features minimized; no duplicate-purpose crates.

## 14. Version control and review

Small, single-purpose commits, imperative subject (`Add X`, `Fix Y`); short-lived branches; every pull request: description (what/why/verified/not verified), linked requirement/invariant ids, tests, docs updated. Review checklist: (1) smallest change? (2) reuse instead of new? (3) invariants and error classes respected? (4) limits and bounds? (5) tests incl. failure paths? (6) names/functions within standards? (7) docs updated? (8) secrets/logging safe? (9) no lint/test weakening? (10) dependency added without approval?

## 15. Definition of Done (code)

Build, `rustfmt`, `clippy -D warnings`, tests (unit, property, integration), contract diff, `cargo deny`, plan check all green; self-review against section 14; summary states verified vs unverified.
