# catalog - test plan

Status: DRAFT

Levels follow the [verification ladder](../../03-correctness/verification-ladder.md). Every REQ-CAT id has at least one row. Property tests use fixed seeds in CI and log the seed on failure.

| ID | Level | What | REQ | INV |
|---|---|---|---|---|
| TST-CAT-001 | model, type | `VersionLifecycle` model: published, archived plus soft delete; a version is born published (D-56); compile-fail test that an illegal transition does not exist; unpublish, restore and delete need `manage_catalog`, not `operate`; a visible version arises only through publish or restore | REQ-CAT-001 | INV-CAT-001 |
| TST-CAT-002 | e2e, prop | Anonymous and signed-in readers get 404 for archived, deleted books, identical to an unknown slug; preview, cover, files, shelf, Kindle of such books too; reader view has no source URL field | REQ-CAT-002 | INV-CAT-002 |
| TST-CAT-003 | db, prop | Tombstone: one shared filter hides the book on every read path; `book.unpublished` written in the same transaction; files, shelf entries, Kindle stop resolving; undelete restores | REQ-CAT-003 | INV-CAT-003 |
| TST-CAT-004 | db, unit | Publish without writer, translator, editor or compiler credit rejected (`no_credit`); a compiler counts as editor; removing the last such credit from a published book fails | REQ-CAT-004 | INV-CAT-004 |
| TST-CAT-005 | db, prop | Duplicate slug rejected; `id` UPDATE rejected; old slug returns 301 and is never reused; no code column exists | REQ-CAT-005 | INV-CAT-005 |
| TST-CAT-006 | db, prop, e2e | Concurrent edits with a stale revision never merge (412); override survives re-import and is flagged stale; history keeps every revision; 0 and null stay distinct | REQ-CAT-006 | INV-CAT-006 |
| TST-CAT-007 | db, prop | Agent merge then split restores credits exactly; names never act as keys; contributor facet matches (role, name) on one credit | REQ-CAT-007 | INV-CAT-007 |
| TST-CAT-008 | prop, e2e | Browse pages (series, category, each role, publisher): displayed count equals result set size | REQ-CAT-008 | INV-CAT-008 |
| TST-CAT-009 | prop, e2e | Anonymous search by title, writer, translator, editor, publisher, series, category returns only published books, ranked; random states x random queries | REQ-CAT-009 | INV-CAT-009 |
| TST-CAT-010 | prop, unit | Normalizer idempotent; golden cases (vowel signs kept in exact key, digits fold, ZWJ/ZWNJ, loose key folds ী/ি ূ/ু ণ/ন শ ষ/স); same version in index and query | REQ-CAT-010 | INV-CAT-010 |
| TST-CAT-011 | gold, review | Latin to Bengali alias matching, both directions | REQ-CAT-011 | INV-CAT-011 |
| TST-CAT-012 | type, e2e | Compile-fail: the indexer accepts only `PublicDocument`; leak canary: a unique token placed in preview text, a non-preview section and a shelf name appears in no public response and no search result | REQ-CAT-012 | INV-CAT-012 |
| TST-CAT-013 | prop, drill | Rebuild from tables equals incremental index on random queries; update searchable within 30 s at p99 | REQ-CAT-013 | INV-CAT-013 |
| TST-CAT-014 | prop, unit | Bengali collation comparator is a total preorder and stable; the `bn` collation exists in the production image | REQ-CAT-014 | INV-CAT-014 |
| TST-CAT-015 | prop | Facets AND across, OR within; facet counts equal result counts for random filters and one snapshot | REQ-CAT-015 | INV-CAT-015 |
| TST-CAT-016 | prop, e2e | Pagination concatenation equals the full list under a fixed snapshot; no repeat or skip; page size and window bounded (limit-1, limit, limit+1) | REQ-CAT-016 | INV-CAT-016 |
| TST-CAT-017 | fuzz, e2e | Query fuzzing: length cap, hostile Unicode, tsquery metacharacters never reach the database as syntax; anonymous endpoints expose only public fields | REQ-CAT-017 | INV-CAT-017 |
| TST-CAT-018 | prop, review | Judged query set (>= 300 queries): MRR@10 >= 0.85, recall@20 >= 0.95 with per-class breakdown and regression diff; gate level SHOULD (O-5) | REQ-CAT-018 | INV-CAT-018 |
| TST-CAT-019 | type, e2e | Preview needs session plus `preview` (a user with only `read` or `browse` is 403); only the stored `PreviewArtifact` is served, 0 characters allowed; `X-Robots-Tag` noindex; no code path from a full document | REQ-CAT-019 | INV-CAT-019 |
| TST-CAT-020 | type, db, e2e | Files reachable only through handlers: no static path, traversal fails, rows write-once, a hash mismatch is found by the verify job and blocks publish and restore | REQ-CAT-020 | INV-CAT-020 |
| TST-CAT-021 | db, model | Version and assets immutable (UPDATE rejected); publish switches the pointer atomically (concurrent readers see old or new, never a mix); previous files kept until the next publish; reprocess creates a new version | REQ-CAT-021 | INV-CAT-021 |
| TST-CAT-022 | model, db, fault | Publish idempotency: replay with the same build identity returns the same version; kill between blob rename and commit leaves no visible or half version; artifacts accepted atomically; version is `published` in the same transaction, with no approval step (D-49); a hash mismatch or missing credit gives a typed 4xx and no version | REQ-CAT-022 | INV-CAT-022 |
| TST-CAT-023 | type, prop | EPUB download needs `download` and a published version; random `Range` requests concatenate to the original bytes | REQ-CAT-023 | INV-CAT-023 |
| TST-CAT-024 | model, prop | Outbox: events in the same transaction (kill test), ordered by cursor, duplicates tolerated by consumers, a restart mid-page repeats at most that page; model checked with the Outbox model | REQ-CAT-024 | INV-CAT-024 |
| TST-CAT-025 | db, e2e | Shelf (user, book) unique and add idempotent; mutation needs `browse` and a session; random grants x shelf membership x book states never change an access decision | REQ-CAT-025 | INV-CAT-025 |
| TST-CAT-026 | prop | Saved filter round trip `apply(save(f)) = f`; duplicate save is a typed 409 | REQ-CAT-026 | INV-CAT-026 |
| TST-CAT-027 | prop, e2e | CSV rows equal list rows for the same filter and snapshot; cells starting with `=`, `+`, `-`, `@` neutralized; control characters quoted; row cap gives `export_too_large`; scope per O-4 | REQ-CAT-027 | INV-CAT-027 |
| TST-CAT-028 | unit, review | Cover validation by bytes (type, size, checksum), allow-listed hosts; generated cover has title and author with no tofu glyph (Bengali shaping fixture) | REQ-CAT-028 | INV-CAT-028 |
| TST-CAT-029 | model, e2e | Kindle: needs `kindle` and a published version; size cap; per-user rate limit; idempotency; event in the same transaction; status callback updates the row and is idempotent; shown on the Files tab | REQ-CAT-029 | INV-CAT-029 |
| TST-CAT-030 | unit, e2e | Uniqueness and state conflicts give typed 409/422 with code and field path; missing or deleted resources are 404, never 500 (table-driven over routes) | REQ-CAT-030 | INV-CAT-030 |
| TST-CAT-031 | db, e2e | Every state change, export and EPUB download appends an audit row with the actor in the same transaction; service role cannot UPDATE or DELETE the audit table | REQ-CAT-031 | INV-CAT-031 |
| TST-CAT-032 | prop, e2e | GET handlers perform no writes (read-only connection; a missing or corrupt blob returns an error and marks nothing failed or queued) | REQ-CAT-032 | INV-CAT-032 |
| TST-CAT-033 | db, prop, type, e2e | Saved filters: owner-only visibility (cross-user table-driven), per-user count bound gives a typed error, JSON validated against the schema on save and apply | REQ-CAT-033 | INV-CAT-033 |
| TST-CAT-034 | e2e | Every `/api/catalog/*` route declares a scope (startup fails otherwise); unscoped route test | REQ-CAT-002, 017 | INV-CAT-002 |
| TST-CAT-035 | fuzz | Intake validation: not-a-zip, zip bomb, wrong mimetype entry, oversized cover, script or SVG in the preview artifact rejected or sanitized | REQ-CAT-020, 028 | INV-CAT-020, 028 |
| TST-CAT-036 | gold | Duplicate match input from ingestion: exact normalized key plus author, category and edition; near-matches listed, never merged; Bengali variants | REQ-CAT-010 | INV-CAT-010 |
| TST-CAT-037 | fault | Reader or notify down: events accumulate, catalog continues; `GET /internal/books` resync equals the event result | REQ-CAT-024 | INV-CAT-024 |
| TST-CAT-038 | e2e | `GET /me/export` returns only the caller's shelf and saved filters; another user's data never appears (D-55) | REQ-CAT-034 | INV-CAT-034 |

Moved elsewhere: build determinism, epubcheck and structure audit, cover rendering are ingestion build-time tests; sanitizer fuzzing of the reading copy is [reader](../reader/test-plan.md).
