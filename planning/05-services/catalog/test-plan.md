# catalog — test plan

Status: DRAFT

| ID | Level | What | Invariant |
|---|---|---|---|
| TST-CAT-001 | model | `BookLifecycle.tla` updated for draft/in_review/published/archived plus soft delete and the intake path | INV-CAT-001 |
| TST-CAT-002 | db | Constraint tests: approve without credit rejected; duplicate slug/code rejected; second published version rejected; old slug resolves 301; code/id UPDATE rejected | INV-CAT-002/003 |
| TST-CAT-003 | prop | Concurrent edits with stale revision never silently merge; override survives re-ingestion and is flagged stale | INV-CAT-004 |
| TST-CAT-004 | prop | Agent merge/split round-trip restores credits exactly | INV-CAT-005 |
| TST-CAT-005 | prop+gold | Duplicate classification vs labeled pairs (five cases, volume 1 vs 10, collection vs component, missing author, deleted book) | INV-CAT-006, INV-ING-015 |
| TST-CAT-006 | prop | Facet count equals result count for random filters | INV-CAT-007, INV-DSC-007 |
| TST-CAT-007 | prop | Export rows equal list rows; CSV escaping of formula characters | INV-CAT-008 |
| TST-CAT-009 | e2e | Anonymous gets 404 for draft, in_review, archived, deleted books, identical to an unknown slug; preview/cover/download of such books are also 404 | INV-CAT-001, INV-ACC-012 |
| TST-CAT-010 | db+fault | Intake idempotency: replay with same `Idempotency-Key` returns same version; crash between blob rename and commit leaves no visible or half version | INV-CON-001 |
| TST-CAT-011 | e2e | Every `/api/catalog/*` route has a declared scope (startup fails otherwise); download without `download` scope = 403; demo mutation refused | INV-CON-004 |
| TST-CAT-012 | e2e | Files are not reachable except through handlers: no static path, traversal attempts fail, hash mismatch on read is detected by verify job | INV-CON-004 |
| TST-CAT-013 | prop | Range requests: random ranges concatenate to the original EPUB | INV-CON-005 |
| TST-CAT-014 | fuzz | Intake validation: not-a-zip, zip bomb, wrong mimetype entry, oversized cover, SVG/script in preview rejected or sanitized; sanitizer idempotent | INV-CON-009 |
| TST-CAT-015 | e2e | Outbox: `GET /internal/events` ordered, complete, duplicates tolerated by consumers; restart mid-page repeats at most that page | INV-ING-016 |
| TST-CAT-016 | e2e | Kindle request: idempotency, size/daily limit, event written in the same transaction (kill test), no request for unpublished book | REQ-CAT (Kindle) |
| TST-CAT-017 | prop | Shelf never changes any access decision: random grants x shelf membership x book states | X3 rule, INV-ACC |
| TST-DSC-001 | prop | Normalizer idempotent; keys stable across versions; same function version in index and query | INV-DSC-002 |
| TST-DSC-002 | gold | Judged query set (>= 300): MRR@10 >= 0.85, recall@20 >= 0.95 with the PostgreSQL configuration; per-class breakdown; regression diff report | INV-DSC-009 |
| TST-DSC-003 | gold | Latin to Bengali alias matching list, both directions | INV-DSC-003 |
| TST-DSC-004 | prop | Rebuild from tables equals incremental search docs (result-set equality on random queries) | INV-DSC-005 |
| TST-DSC-005 | prop | Pagination concatenation equals full list for a fixed data state | INV-DSC-008 |
| TST-DSC-006 | type+e2e | No code path from non-preview text to the indexer (compile-fail test); leak canary: unique token placed after the preview cut appears in no public response and no search result | INV-DSC-004, INV-CON-003 |
| TST-DSC-007 | prop | Bengali collation ordering (`bn` ICU collation) is a total preorder; the ICU collation exists in the production image | INV-DSC-006 |
| TST-DSC-008 | e2e | Archive/delete removes the book from search in the same transaction (no window) | INV-DSC-001 |
| TST-DSC-009 | gold | Bengali normalization golden cases: vowel signs preserved in exact key, punctuation becomes a separator, digits fold, nukta forms equal, loose key folds ী/ি etc. | INV-DSC-002 |

Moved to ingestion test plan (build-time properties): build determinism (was TST-CON-003), epubcheck and structure audit (TST-CON-009), cover rendering (TST-CON-010).
