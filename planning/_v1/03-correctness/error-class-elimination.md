# Error-class elimination catalog

Status: DRAFT

For each class of defect that plagued the legacy system or is typical for this
domain: how it becomes impossible (**P**), measured (**M**) or detected (**D**).

| # | Error class | Legacy symptom | Elimination | Class | Invariant |
|---|---|---|---|---|---|
| 1 | Null / missing value | `None` handling bugs in views | `Option`/`Result` only; no sentinel strings; deserialization rejects unknown/missing fields | P | INV-PLT-002 |
| 2 | ID mix-ups | UUID of book passed as user id | Newtypes `BookId`, `AccountId`, `SectionId`… (no `From<Uuid>` outside constructors) | P | INV-PLT-002 |
| 3 | Contract drift between services | Frontend/backend mismatches, regenerated OpenAPI | Contract crates are the only source of wire types; generated server stubs and clients | P | INV-PLT-002 |
| 4 | SQL/schema mismatch | Runtime `FieldError` | `sqlx` compile-time checked queries against the migrated schema; CI builds against a live migrated DB | P | INV-PLT-001 |
| 5 | Illegal state transitions | Requests stuck in odd states across `processing` and `ingestion` | State enums + transition functions; no public setter for state; TLA+ models for job/session/account lifecycles | P | INV-ING-010, INV-IDN-008 |
| 6 | Race conditions | Duplicate submissions, double mark | Unique/exclusion constraints, `FOR UPDATE SKIP LOCKED` claims, fencing epochs, optimistic revisions | P/db | INV-ING-010, INV-CAT-004 |
| 7 | Duplicate side effects | Retried tasks send mail twice | Idempotency keys, dedupe tables committed with effect, outbox | P | INV-PLT-003, INV-PLT-009 |
| 8 | Lost events | Dispatch failure fallback to inline | Transactional outbox; relay at-least-once; consumer idempotent | P | INV-PLT-009 |
| 9 | Authorization holes | Per-view `if` checks; permissions in `common` | Single `decide`; handlers require `Decision::Allow` witness; Alloy-checked rules | P | INV-ACC-003 |
| 10 | Content leaks | Preview vs full text paths | Preview is a separate build-time artifact type; public index consumes `PublicDocument` only | P | INV-CON-003, INV-DSC-004 |
| 11 | Stale/forged access | Long-lived tokens | Signed capabilities ≤ 5 min bound to subject, book, artifact set, action | P | INV-ACC-008 |
| 12 | Panics in request path | 500s | Lints deny `unwrap`, `expect`, indexing, `panic!`; fuzzing on parsers; `catch_unwind` boundary only as safety net + alert | P/fuzz | INV-PLT-004 |
| 13 | Unbounded resources | Giant HTML bodies, runaway jobs | Explicit limits table; every channel, query, body, timeout, retry bounded | P/prop | INV-PLT-005 |
| 14 | Time bugs | Timezone display bugs, expiry skew | Injected `Clock`; UTC storage; zone only at the edge | P | INV-PLT-010 |
| 15 | Unicode / normalization bugs | Variant spellings split authors; digit mismatches | `Normalized<Bn>` newtype constructed only through the one normalizer; idempotency property | P/M | INV-DSC-002 |
| 16 | HTML injection | Stored scraped HTML rendered | `SafeHtml` newtype from sanitizer only; idempotent sanitizer; CSP | P | INV-CON-009 |
| 17 | Silent data loss in processing | Unclassified text dropped | Conservation invariant checked at the end of every pipeline run; runtime assertion refuses to publish | P | INV-ING-002 |
| 18 | Heuristic regressions | New rule fixes one book, breaks others | Rulesets versioned, gold-set gate, diff on reprocess | M | INV-ING-011 |
| 19 | Incomplete books published | 5%/33% tolerance, pinned chapter | Completeness proof: every TOC leaf fetched or recorded empty | P | INV-ING-006 |
| 20 | TOC/nav disagreement | "nav self-link", missing parent | Both rendered from one `SectionTree`; epubcheck + own audit | P | INV-ING-003, INV-CON-007 |
| 21 | Non-deterministic output | Regeneration changes bytes | Pure builders, sorted maps, fixed timestamps, reproducible ZIP | P | INV-CON-002 |
| 22 | Broken annotations on rebuild | CFI orphaned | Section ids + text-quote anchors + re-anchor algorithm with Orphaned state | P/M | INV-LIB-002 |
| 23 | Version skew between services | n/a (monolith) | Startup compatibility handshake; contract version in every message | P | INV-PLT-001 |
| 24 | Configuration errors | Missing env var discovered at runtime | Typed config parsed at startup; unknown/missing → exit with error | P | INV-PLT-001 |
| 25 | Migration data loss | Schema removals without plan | Idempotent steps, reconciliation report, rollback rehearsal | D/drill | INV-MIG-001 |
| 26 | UI states forgotten | Blank pages on error | Exhaustive page-state enum | P | INV-WEB-001 |
| 27 | Dead links / routes | Legacy redirects pile up | Route map is the single source; link checker in CI | P/e2e | INV-WEB-002 |
| 28 | Source site misbehaviour | Partial fetches, locked chapters | Read-only acquisition, retry/backoff, drift detector, quarantine | D | INV-ING-012 |
| 29 | Dependency vulnerabilities | n/a | `cargo audit`, `cargo deny`, pinned lockfile, minimal dependency policy | D | INV-PLT-004 |
| 30 | Operator error | Manual scripts | Runbooks, scripted deploy, restore drills, dry-run modes | D/drill | INV-PLT-008 |
