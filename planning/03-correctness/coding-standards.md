# Coding standards (Rust and supporting practices)

Status: DRAFT

Complements [type-driven design](type-driven-design.md) (error elimination) and the [engineering philosophy](../00-charter/engineering-philosophy.md) (rules). Items marked **verify** must be confirmed against the installed tool's documentation before being relied on (we do not invent flags).

## 1. Function and module shape

| Rule | Limit | Enforcement (config keys **verified** in the clippy docs 2026-11-17; defaults in brackets) |
|---|---|---|
| Function length | ~20 lines (hard cap 30) | `too-many-lines-threshold = 30` [default 100] configures `too_many_lines` (the ~20 target is a review rule) |
| Parameters | ≤ 3 | `too-many-arguments-threshold = 3` [default 7] configures `too_many_arguments` |
| Nesting | ≤ 2 levels of control flow | `excessive-nesting-threshold = 2` [default 0] configures `excessive_nesting` (the config key exists; the lint's group and exact behavior are **still to verify** at G1); `cognitive-complexity-threshold` [default 25] for `cognitive_complexity`; review |
| Module size | ≤ ~300 lines; one concept per module | review; size check script |
| File per crate responsibility | `lib.rs` re-exports only | review |

Techniques: early return, `?`, `let … else`, iterator chains, small helper functions with intention-revealing names, parameter structs, enums instead of bool flags.

## 2. Naming and style

Rust API Guidelines naming (RFC 430): `snake_case` fns/vars, `CamelCase` types, `SCREAMING_SNAKE_CASE` consts; conversions `as_`/`to_`/`into_`; getters without `get_`; no abbreviations (`account`, not `acct`); booleans read as predicates (`is_active`). Format with `rustfmt` (default config, checked in CI). Lint with `clippy` (`-D warnings`) with the deny set below.

## 3. Lints (workspace `Cargo.toml`)

Syntax **verified** (Cargo reference): `[workspace.lints.rust]` / `[workspace.lints.clippy]` in the root manifest, each member opts in with `[lints]` + `workspace = true` (Rust ≥ 1.74); `priority` orders lint groups; Cargo applies lints only to workspace members, not dependencies. `integer_arithmetic` no longer exists (renamed past name of `arithmetic_side_effects`, group *restriction*). Group membership of the other named lints is still **to verify** at G1 (docs.rs/clippy index read only partially).

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

Build, `rustfmt`, `clippy -D warnings`, tests (unit, property, integration), contract diff, `cargo deny`, plan check all green; self-review against section 14; summary states verified vs unverified. For the web app add: TypeScript compile (strict), ESLint, template type-check, unit tests, Playwright journeys, axe scan, generated-client diff (§16).

## 16. TypeScript and Angular (web UI)

The owner's rules apply unchanged (20 lines, ≤ 3 parameters, ≤ 2 nesting, no magic numbers, no flags, comments say *why*). Tool names below are the usual ones; **verify exact rule names and config keys against the installed versions at gate G1/S-02** before relying on them.

| Topic | Rule | Enforcement |
|---|---|---|
| Compiler | `strict` plus `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `noImplicitReturns` (all **verified** to exist); Angular `strictTemplates` (exists; default `true`) and `strictInjectionParameters` (exists; default `false`, recommended `true`) | `tsconfig`, Angular compiler |
| No escape hatches | no `any` (`no-explicit-any`, in the *recommended* preset), no non-null `!` (`no-non-null-assertion`, in the *strict* preset), no `as` casts except in the generated-client boundary and parsers with a `// why:` note (`consistent-type-assertions` with `assertionStyle: 'never'`, a *stylistic*-preset rule), no `any` flowing in (`no-unsafe-assignment`, *recommended-type-checked*), `ban-ts-comment` (*recommended*; `@ts-expect-error` only with a description) — presets **verified** in typescript-eslint docs 2026-11-17 | typescript-eslint rules (enable the `strict-type-checked` + `stylistic-type-checked` configs; names to confirm at S-02) |
| Magic numbers | the core `no-magic-numbers` rule is *frozen*; use typescript-eslint's `no-magic-numbers` extension and turn the core rule off | ESLint |
| Shape | `max-params` `{max: 3}` [default 3], `max-lines-per-function` `{max: 30, skipBlankLines: true, skipComments: true}` [default 50], `max-depth` `{max: 2}` [default 4], `complexity` `{max: 10}` [default 20] (option names **verified** in the ESLint docs 2026-11-17) | ESLint core rules |
| Exhaustiveness | discriminated unions for states, results and errors; `switch` ends with an `assertNever(x: never)`; `@typescript-eslint/switch-exhaustiveness-check` (needs type information and is **not** in any preset — enable explicitly) | compiler + ESLint |
| Immutability | `readonly` by default, `ReadonlyArray`, no mutation of inputs; Angular signals for state, derived state via `computed` | review + lint |
| Wire types | only from `core/api/generated`; runtime-validate untrusted JSON at the boundary if the generator does not | Q3 diff |
| Components | standalone, `OnPush`, small (template + class ≲ 150 lines), presentational vs container split, no logic in templates beyond trivial expressions, inputs/outputs typed, no direct DOM access except through CDK/renderer services | review + lint |
| Subscriptions | prefer signals / `async` pipe / `takeUntilDestroyed`; no manual subscribe without teardown | lint + review |
| HTTP | only in `core/`; every call has a typed result, timeout and error mapping to `ErrorCode` | review + tests |
| Security | no `innerHTML` except through the approved sanitizing component for chapter HTML; strict CSP (no inline scripts); no secrets in the bundle; never log personal data | lint rule + e2e CSP check |
| Accessibility | Angular Material/CDK a11y primitives (focus trap, live announcer, key manager); every interactive element labeled; axe in CI | e2e |
| i18n | all strings through the i18n catalog (`bn`, `en`); key parity test (INV-WEB-009) | unit |
| Style | tokens only; no hard-coded colors/px for theme-able values; no `!important`; no deep `::ng-deep` | stylelint (to verify) |
| Naming | `kebab-case` files, `PascalCase` classes, intention-revealing names, no abbreviations | lint |
| Performance | lazy-loaded feature routes, `@defer`/image `loading=lazy` where appropriate, budgets in [performance](../09-testing/performance.md); measure before optimizing | CI budgets |
| Testing | unit tests for logic (pure functions first), component tests for states, Playwright for journeys, no sleeps; deterministic via fake timers/clock | CI |
| Dependencies | each npm package approved and registered; lockfile managed only by the package manager; `npm audit` (or equivalent) in nightly | Q10 |
