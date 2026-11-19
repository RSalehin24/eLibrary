# Test strategy

Status: DRAFT

## Pyramid (by count and by what each level proves)

| Level | Share | Proves | Tooling |
|---|---|---|---|
| Compile-time / lints | all code | type-level invariants | rustc, clippy, `trybuild` compile-fail tests |
| Unit + property | ~60% | pure logic: normalizer, decide, tree, conservation, anchors, duplicate policy | `proptest`, `insta` |
| Model checking | small, nightly | concurrency/protocol invariants | TLC, Alloy |
| Model-based | state machines | implementation follows the model | TLC trace export → Rust replay |
| Service integration | ~25% | handlers + DB + constraints, outbox/inbox, idempotency | ephemeral Postgres (`testcontainers`/local), fake clock |
| Contract | per pair | callers/callees agree | generated schema diff + consumer-driven checks |
| E2E | ~10% | user journeys across services and browsers | Playwright (Chromium, Firefox, WebKit), axe |
| Corpus | per ruleset/analyzer | extraction, structure, search quality | gold runner (CLI), metrics gates |
| Fault injection | targeted | recovery behavior | kill points, toxiproxy, disk-full, clock skew |
| Load | pre-release | capacity and SLOs | k6 |
| Security | pre-release | abuse resistance | threat-model cases, fuzzing, dependency audit |

## Rules

1. **Every `TST-*` in a service test plan is implemented and tagged** with its invariant id in the test name; a script lists invariants lacking a passing test (Q7 extension at G3+).
2. Property tests have a recorded seed on failure and shrink; regressions become permanent example tests.
3. No test depends on wall-clock, network or order; time and randomness are injected.
4. Integration tests use real PostgreSQL, never mocks of the database.
5. Peer services in single-service tests are replaced by fakes generated from the contract crates (same types), plus at least one pairwise contract test.
6. Flaky tests are quarantined within a day with an owner and a deadline of seven days; quarantine count is reported.
7. Mutation testing (`cargo-mutants`) on `domain-access`, `domain-document`, `domain-entities`, `domain-anchor` — score ≥ 85%.
8. Golden-file (insta) snapshots are reviewed in diffs; snapshot updates require an explanatory commit message.
9. Test data: synthetic seeds for functional tests; gold corpus only for corpus tests; production data never in tests.

## E2E critical journeys (must pass before every release)

F1 discover → preview → sign in → read · F2 highlight/progress/resume · F3 admin creates a book from a fixture source · F4 review resolution · F5 reprocess diff apply · F6 invite → activate → TOTP · F7 Kindle send (sink) · F8 curate catalog with conflict. Matrix: {Chromium, Firefox, WebKit} × {bn, en} × {360 px, 1280 px} × {light, dark} for F1 and F2; the others on Chromium + one more.

## Test environments

`xtask test` (local, all fakes), `xtask test --integration` (Postgres), `xtask e2e` (full stack + fixture source server that serves recorded LearnDash pages), `xtask gold` (corpus), `xtask models` (TLC/Alloy).
