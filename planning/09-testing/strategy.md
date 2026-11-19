# Test strategy

Status: DRAFT (six-service design; D-29, D-31, D-32, D-47)

Six Rust services (gateway, identity, catalog, reader, ingestion, notify) plus the Angular SSR `web`, all run in Docker Compose. Every service test plan (`05-services/*/test-plan.md`) holds the `TST-*` rows; this file holds the levels, the rules, the environments, the web rows and the end-to-end journeys. The legacy tests protected only helper functions and happy paths (no permission, state-visibility, ticket or job-recovery tests); the levels below exist to close exactly those gaps. Kept from v1: pyramid, rules 1-9. Changed: Compose stack replaces per-service fakes for e2e, six services, no migration tests (D-32), source-site fixtures replace the live site.

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

## Web test plan (rows carried from the web README; there is no separate web test-plan file, O-10 resolved here)

Levels: `unit` (Angular runner, real units, schema-generated mocks), `type`, `e2e` (Playwright on the Compose stack, hermetic, no fixed sleeps), `static`. Every acceptance criterion of REQ-WEB maps to a row.

| ID | Level | Behaviour | REQ |
|---|---|---|---|
| TST-WEB-001 | type, e2e | `PageState` has Loading, Empty, Ready, Error, Forbidden, NotFound, Offline; a missing variant fails compilation; each state rendered in the matrix | REQ-WEB-001 |
| TST-WEB-002 | unit, e2e | 401 goes to sign-in and keeps the target; 403 keeps the session and shows the reason; `mfa_required` goes to TOTP | REQ-WEB-002, 020 |
| TST-WEB-003 | unit, e2e | guards and navigation built from capabilities, per role (reader, operator, admin); direct URL refused | REQ-WEB-003, 014 |
| TST-WEB-004 | e2e | link checker over the typed route table; unknown route gives NotFound | REQ-WEB-004 |
| TST-WEB-005 | e2e, review | minimalist rules; screenshot checks at the three widths in both themes | REQ-WEB-005, 006 |
| TST-WEB-006 | e2e | theme: System, Light, Dark; applied before first paint; follows `prefers-color-scheme`; persists | REQ-WEB-007 |
| TST-WEB-007 | e2e | automated contrast checks (4.5:1 text, 3:1 UI) in both themes on every screen | REQ-WEB-008 |
| TST-WEB-008 | e2e | 360 to 1920 px, no horizontal scroll, orientation change keeps form state; window classes compact, medium, expanded, large | REQ-WEB-009 |
| TST-WEB-009 | e2e | axe, keyboard operation, focus visible, dialogs trap focus, 200% text scale, reduced motion | REQ-WEB-010, NFR-008 |
| TST-WEB-010 | unit, static | `bn` and `en` catalogs have identical keys (build fails otherwise); no hard-coded text | REQ-WEB-011, NFR-010 |
| TST-WEB-011 | e2e | Bengali rendering: conjuncts and vowel signs intact, self-hosted fonts, no uppercase transform | REQ-WEB-012 |
| TST-WEB-012 | static, CI | codegen produces no diff; `any`, non-null assertion and unchecked cast only in the generated boundary; no HTTP call outside `core/` | REQ-WEB-013, 023 |
| TST-WEB-013 | e2e | Library: filters and sort in the URL, chips, card/list toggle, saved filters, Bengali-aware sort | REQ-WEB-015 |
| TST-WEB-014 | e2e | Book detail: tabs, scope-gated download and Kindle actions, honest read-limit notice, Read opens through a ticket | REQ-WEB-016 |
| TST-WEB-015 | e2e | Import workspace: bucket rail, confirm dialogs, snackbar results, live SSE update and reconnect with snapshot | REQ-WEB-017 |
| TST-WEB-016 | e2e | Users and access: batched atomic grants, per-user drawer, audit view | REQ-WEB-018 |
| TST-WEB-017 | e2e | Settings: re-authentication stepper for TOTP, preferences, own data export | REQ-WEB-019 |
| TST-WEB-018 | unit, e2e | CSRF refresh and one retry; backoff on 429, 503, 504; no health poll; form state kept | REQ-WEB-020 |
| TST-WEB-019 | type, e2e | ticket held in memory only (not in URL, storage, logs); header `X-Reader-Ticket`; one refresh on `ticket_expired`; progress flushed on `visibilitychange` and `pagehide` | REQ-WEB-021 |
| TST-WEB-020 | e2e | first HTML of public pages carries title, canonical, meta, structured metadata; preview is `noindex`; SSR keeps no cross-request user state; SSR failure shows a typed page | REQ-WEB-022, 024 |

Security headers on pages are **OPEN (O-2)**.

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
