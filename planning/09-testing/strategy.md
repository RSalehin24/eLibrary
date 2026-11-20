# Test strategy

Status: DRAFT (six-service design; D-29, D-31, D-32, D-47)

Six Rust services (gateway, identity, catalog, reader, ingestion, notify) plus the Angular SSR `web`, all run in Docker Compose. Every service test plan (`05-services/*/test-plan.md`) holds the `TST-*` rows; this file holds the levels, the rules, the environments, the end-to-end journeys. The legacy tests protected only helper functions and happy paths (no permission, state-visibility, ticket or job-recovery tests); the levels below exist to close exactly those gaps. Kept from v1: pyramid, rules 1-9. Changed: Compose stack replaces per-service fakes for e2e, six services, no migration tests (D-32), source-site fixtures replace the live site.

## Pyramid

| Level | Share | Proves | Tooling |
|---|---|---|---|
| Compile-time and lints | all code | type-level invariants | rustc, clippy, `trybuild` compile-fail tests, strict TypeScript, ESLint |
| Unit and property | ~60% | pure logic: sanitizer, anchors, Bengali normalizer, duplicate key, decide, state machines | `proptest`, `insta`, Angular unit runner |
| Model checking | small, nightly | protocol and concurrency invariants (job lease, outbox, ticket, publish saga) | TLC |
| Service integration (`db`) | ~25% | handlers, real PostgreSQL, constraints, outbox, idempotency | ephemeral PostgreSQL, fake clock |
| Contract | per pair | caller and callee agree | schema generated from the Rust contract crates; diff and generated-fake checks |
| E2E | ~10% | journeys across the whole stack and browsers | ephemeral Compose stack, Playwright, axe |
| Corpus (`gold`) | per ruleset | extraction, structure, duplicate policy, search quality | gold runner, see [gold corpus](../06-data/gold-corpus/README.md) |
| Fault injection | targeted | recovery | [fault injection](fault-injection.md) |
| Load | pre-release | capacity and latency | [performance](performance.md) |
| Security | pre-release | abuse resistance | threat-model cases, fuzzing, dependency audit |

## Rules

1. Every `TST-*` row is implemented and the test name carries its invariant id; a script lists invariants with no passing test.
2. Property tests record the seed on failure and shrink; each regression becomes a permanent example test.
3. No test depends on wall clock, live network or order; time and randomness are injected. **No test or CI job contacts the live source site**: acquisition tests use recorded fixtures served by a fixture server (see Source fixtures).
4. Integration tests use real PostgreSQL, never a database mock.
5. In single-service tests, peer services are fakes generated from the contract crates (same types); each caller-callee pair also has one contract test and one Compose e2e path.
6. Flaky tests are quarantined within one day with an owner and a seven-day deadline; the quarantine count is reported.
7. Mutation testing (`cargo-mutants`, nightly) on the pure cores: sanitizer, anchors, normalizer and duplicate key, authorization decision, job lifecycle. Score at least 85%.
8. Snapshots (`insta`) are reviewed in diffs; an update needs an explanatory commit message.
9. Test data is synthetic (see [seed and fixtures](../06-data/seed-and-fixtures.md)); the gold corpus is used only by corpus tests and is never committed (CLAUDE.md); production data is never used.
10. epubcheck (D-47) runs in the ingestion worker before publish, so integration tests of the build path run it against generated EPUBs; the worker image therefore carries a Java runtime (approval at P1); if epubcheck cannot run, the publish gate fails closed (D-57, TST-ING-043). Whether CI also runs it separately is not needed: the same check runs in the e2e publish path.

## Ephemeral Compose stack (integration and e2e)

`xtask e2e` brings up a project-scoped stack from the production Compose file plus a test override: all services and `postgres` (one database and role per service), `web`, `caddy` with an internal certificate, plus test-only containers `mail-sink` (SMTP capture with an HTTP read API) and `source-fixture` (serves recorded source pages, can inject faults). Every run uses a fresh project name and volumes, waits for readiness within the 90 s start target (REQ-NFR-014), seeds through the same first-admin command as production plus a test-only seed container that is absent from production images (REQ-IDN-032), and is torn down with its volumes. Services are tested through the gateway only, never through a published service port. Memory limits equal the production limits so that limit breaches show up.

## Contract tests

The schemas are generated from the Rust contract crates (`xtask codegen`). Checks: (a) regenerating changes nothing (CI fails on diff); (b) breaking change of a published schema needs a version bump; (c) the web generated client and the service fakes come from the same schema; (d) every `/api/*` route declares a required scope, and a route without one fails startup (TST-GWY, TST-IDN); (e) the internal event payloads of `book.published`, `book.unpublished`, `book.version_changed`, `user.disabled`, `grant.changed`, `email.requested`, `kindle.requested` validate against the schema in both producer and consumer tests.

## Property and fuzz targets

| Target | Properties | Source rows |
|---|---|---|
| Reader sanitizer (allow-list) | no script, handler, remote reference or external style survives; idempotent; text preserved | TST-RDR-003 and TST-RDR-029 (fuzz) |
| Anchors | anchor then resolve returns the same range; re-anchoring after a new version follows D-46; no panic on any input | TST-RDR-016, TST-RDR-025 |
| Bengali normalizer | vowel signs and conjuncts preserved; normalization idempotent; different words never collide; equal visual forms collapse | TST-ING-023, TST-CAT-009/010 |
| Duplicate key | exact normalized key plus author, category, edition; no substring match; order independent; near-matches listed, never merged | TST-ING-020, 021, 023, 024 |
| EPUB builder | same input gives the same bytes; escaped output; XML well-formed | TST-ING-026, TST-ING-027, TST-ING-028, REQ-NFR-012 |
| Gateway and identity parsers | headers, cookies, CSRF, ticket and token parsing never panic | TST-GWY-006, TST-IDN-028, 041, 042 |
| Search query parser | no panic; Bengali and Latin queries | TST-CAT-017, 035 |

Fuzzing: 256 cases per PR, 10,000 nightly, 30 min per target nightly; seeds and the crash corpus are kept in the repository when they contain no third-party content.

## Source fixtures (no live site in CI)

Recorded and hand-made pages of the source site live in `fixtures/source/`, synthetic where possible (invented titles and text) and minimal excerpts only when a structure cannot be reproduced; no full third-party book is committed (CLAUDE.md). `source-fixture` serves them by path and can answer with 404, 429 with `Retry-After`, 5xx bursts, timeouts, truncated bodies, redirect loops, a 50 MiB page, a 200 sentinel page (login or bot page), and an expired-cookie response. Canary pages of each structure shape detect drift (TST-ING-042). Ingestion tests assert no non-GET request ever reaches the fixture server (D-03, TST-ING-011).

## Web test plan

The web rows (TST-WEB-001..020) live in [05-services/web/test-plan.md](../05-services/web/test-plan.md) like every other service (D-83). Security headers on pages are set by the web container (D-77).

## E2E critical journeys (must pass before every release)

Playwright runs against the ephemeral Compose stack with the seed accounts.

| ID | Journey |
|---|---|
| J1 | Browse and search as anonymous (metadata only), open detail, sign in, preview, read |
| J2 | Highlight, bookmark, note, progress; close and resume; ticket expiry refresh |
| J3 | Invite, accept, set password, TOTP; password reset (mail from the mail sink) |
| J4 | Operator: sync catalog from the source fixture, create request, scrape, curate, duplicate review, build; every gate passes and the book is published automatically (no approval step, D-49); the book appears and reader copy exists; a variant with a failed gate stays in the review queue and nothing is visible |
| J5 | New version: version change, reader copy rebuilt, annotations follow D-46 |
| J6 | Download and Kindle send (mail sink) with delivery status; read-once consumed on redemption |
| J7 | Admin: grants, role change, disable user (sessions and tickets stop), audit entry |
| J8 | Source credential: cookie expired, request waits, replaced, request resumes |

Matrix: J1 and J2 in Chromium, Firefox and WebKit, at 360, 768 and 1280 px wide, in light and dark, in `bn` and `en`; J3 to J8 in Chromium plus WebKit at 360 and 1280 px, in light and dark. Android Chrome and iOS Safari 16 are covered by emulation (REQ-NFR-009).

## Test environments

`xtask test` (unit and property, fakes), `xtask test --integration` (ephemeral PostgreSQL), `xtask e2e` (Compose stack above), `xtask gold` (corpus, local only), `xtask models` (TLC), `xtask load` (performance). CI gates are in [quality gates](../03-correctness/quality-gates.md); the ladder in [verification ladder](../03-correctness/verification-ladder.md). Memory for heavy jobs is capped (owner rule): wrap in `ulimit -v` and `timeout`.
