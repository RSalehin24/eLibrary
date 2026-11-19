# Error-class elimination catalog

Status: DRAFT

Rebuilt 2026-11-19 for the six-service design. For each class of defect that plagued the legacy system (`_replan/analysis/X1-issues-register.md`, ids `X1-nnn`) or is typical for this domain: how it becomes impossible (**P**), measured (**M**) or detected (**D**). The invariant column uses the ids of the rebuilt [register](invariants-register.md). Kept from v1: the idea, the numbering of classes 1 to 30 where the class survives; changed: mechanisms (no capability tokens, no migration, tickets verified by identity, Compose).

| # | Error class | Legacy symptom | Elimination | Class | Invariant |
|---|---|---|---|---|---|
| 1 | Null / missing value | `None` handling bugs in views | `Option`/`Result` only; no sentinel strings; deserialization rejects unknown or missing fields | P | INV-PLT-005 |
| 2 | ID mix-ups | book id passed as user id | Newtypes `BookId`, `UserId`, `VersionId`... with no `From<Uuid>` outside constructors; branded ids in TypeScript | P | INV-PLT-005, INV-WEB-013 |
| 3 | Contract drift between services and web | frontend and backend mismatches (X1-056, X1-092) | Contract crates are the only source of wire types; generated server stubs, fakes and the TypeScript client; regenerate-and-diff in CI (Q3) | P | INV-PLT-005, INV-WEB-013 |
| 4 | SQL and schema mismatch | runtime `FieldError` | `sqlx` compile-time checked queries against the migrated schema; enum columns with CHECK or enum types (X1-034) | P | INV-PLT-023 |
| 5 | Illegal state transitions | requests stuck in odd states (X1-053, X1-031) | State enums, one transition function per edge, no public setter; TLA+ models for account, version, request, job and ticket lifecycles | P | INV-IDN-009, INV-CAT-001, INV-ING-008 |
| 6 | Race conditions | duplicate submissions, check-then-create (X1-039, X1-051) | Unique and exclusion constraints, `FOR UPDATE SKIP LOCKED` claims, lease epochs, optimistic revisions | P | INV-ING-004, INV-CAT-006, INV-ING-033 |
| 7 | Duplicate side effects | retried tasks sent mail twice | Idempotency keys, dedupe in the same transaction as the effect, outbox with pull cursor | P | INV-PLT-006, INV-NTF-001 |
| 8 | Lost events | dispatch failure fell back to inline execution (X1-066, X1-067) | Transactional outbox; at-least-once pull; idempotent consumers; no inline execution anywhere | P | INV-PLT-010, INV-PLT-017, INV-RDR-024 |
| 9 | Authorization holes | self-granted ownership, wildcard roles, AllowAny (X1-001, X1-002, X1-008) | One decision in identity, deny by default; every route declares a scope or startup fails; ownership and shelf grant nothing; Alloy-checked rules | P | INV-IDN-013, INV-IDN-015, INV-IDN-024 |
| 10 | Content leaks | drafts visible, preview and full text on one path (X1-009, X1-010) | Only published, non-deleted versions are visible; `PublicDocument` is a separate type; public routes carry metadata only (D-34) | P | INV-CAT-002, INV-CAT-012, INV-IDN-016 |
| 11 | Stale or forged access | token in URL, never revoked (X1-003) | Reading ticket in a header, 15 minutes, bound to user, book and version, hashed at rest, verified by identity at every redemption (D-37) | P | INV-IDN-021, INV-RDR-006, INV-RDR-007 |
| 12 | Panics in request path | 500s | Lints deny `unwrap`, `expect`, indexing, `panic!`; fuzzing on parsers; the process-boundary catch only logs and alerts | P/fuzz | INV-PLT-007 |
| 13 | Unbounded resources | giant HTML bodies, runaway jobs (X1-068, X1-082) | Explicit limits table; every channel, query, body, timeout, retry and page budget bounded; container memory limits | P/prop | INV-PLT-008, INV-NFR-006 |
| 14 | Time bugs | timezone and expiry skew | Injected `Clock`; UTC storage; zone only at the edge; tickets and sessions follow identity's clock only | P | INV-PLT-011 |
| 15 | Unicode and normalization bugs | vowel signs lost, substring matching (X1-046) | `Normalized<Bn>` only through the one normalizer; idempotency property; labeled normalizer cases in the gold corpus | P/M | INV-ING-022 |
| 16 | HTML injection | stored scraped HTML rendered, autoescape off (X1-004) | `SafeHtml` from the allow-list sanitizer only; idempotent sanitizer; escaping always on; strict CSP | P | INV-RDR-003, INV-ING-024 |
| 17 | Silent data loss in processing | unclassified text dropped, truncation (X1-029) | Conservation invariant at the end of every run; limit-caused omission is a validation error | P | INV-ING-014, INV-ING-018 |
| 18 | Heuristic regressions | one rule fixes a book, breaks others | Versioned rulesets, gold-corpus gate on holdout, diff on reprocess | M | INV-ING-019 |
| 19 | Incomplete books published | 5%/33% tolerance (X1-047) | Completeness proof: every TOC leaf fetched or recorded empty; one threshold constant | P | INV-ING-018 |
| 20 | TOC and nav disagreement | nav self-link, missing parent (X1-060) | TOC, nav and NCX rendered from one `SectionTree`; in-process structure audit and epubcheck in the worker (D-47) | P | INV-ING-015, INV-ING-026 |
| 21 | Non-deterministic output | regeneration changes bytes, random UUID per build | Pure builders, sorted maps, fixed timestamps, reproducible ZIP | P | INV-NFR-012, INV-ING-024 |
| 22 | Broken annotations on a new version | orphaned positions (X1-057, X1-094) | Section ids plus text-quote anchors; server re-anchoring onto a new published version, unmatched kept and flagged orphaned (D-46) | P/M | INV-RDR-015 |
| 23 | Version skew between services | n/a (monolith) | Contract version in every internal message; startup compatibility check; internal service token | P | INV-PLT-003, INV-PLT-020 |
| 24 | Configuration errors | missing env var found at runtime, unsafe defaults (X1-002) | Typed config parsed at startup; a missing or unknown value is a typed startup error | P | INV-PLT-003 |
| 25 | Lost state on restore | no backups (X1-080) | Monthly full backup, restore drill into an empty stack, outbox cursors reconcile after restore (D-33) | D/drill | INV-PLT-015, INV-NFR-004 |
| 26 | UI states forgotten | blank pages on error (X1-093) | Exhaustive page-state union with `assertNever` | P | INV-WEB-001 |
| 27 | Dead links and routes | broken deep links (X1-092) | One typed route table; link checker in e2e | P/e2e | INV-WEB-004 |
| 28 | Source site misbehaviour | partial fetches, challenge pages (X1-074) | GET-only client (D-03), typed outcomes, bounded retries, visible credential status, canary fixtures, quarantine | D | INV-ING-010, INV-ING-006 |
| 29 | Dependency vulnerabilities and drift | n/a | `cargo audit`, `cargo deny`, `npm audit`, pinned lockfiles, register check (Q5, Q10) | D | INV-PLT-013 |
| 30 | Operator error | manual scripts, destructive deploys (X1-081, X1-083) | Runbooks, scripted rolling restart, dry-run modes, previous image kept until the new one is healthy | D/drill | INV-PLT-022 |
| 31 | Gateway and edge bypass (*new*) | `/media/` served unauthenticated (X1-011) | Caddy and gateway hold no file root; only services stream files after a check; every upstream request needs an identity Allow or a listed public route | P/e2e | INV-GWY-002, INV-GWY-011 |
| 32 | Secret exposure (*new*) | secrets printed and copied (X1-013, X1-015) | Secrets as read-only mounted files; `Secret<T>` type; no secret in an image, log, argv or the repository | P/static | INV-IDN-003, INV-PLT-016 |
| 33 | Mixed-up publication state (*new*) | status stored in five places (X1-030) | One status column per entity with CHECK; derived values computed, never stored twice | P | INV-PLT-023 |
| 34 | SSR leaks (*new*, D-39) | n/a | The SSR server calls only the generated client, holds no secret, renders metadata-only public pages; preview text and reading need a session | P/e2e | INV-WEB-022, INV-WEB-024 |
| 35 | Cross-service data access (*new*) | shared tables in the monolith | One database and role per service; no service-to-service dependency edge except contracts | P/static | INV-PLT-002, INV-NFR-011 |
