# catalog — test plan

Status: DRAFT

| ID | Level | What | Invariant |
|---|---|---|---|
| TST-CAT-001 | model | `BookLifecycle.tla` | INV-CAT-001 |
| TST-CAT-002 | db | Constraint tests: Published without credit rejected; duplicate slug/code rejected; slug redirect resolves | INV-CAT-002/003 |
| TST-CAT-003 | prop | Concurrent edits with stale revision never silently merge | INV-CAT-004 |
| TST-CAT-004 | prop | Merge/split round-trip restores credits exactly | INV-CAT-005 |
| TST-CAT-005 | prop+gold | Duplicate classification vs labeled pairs (all five cases + exact duplicate + needs-review) | INV-CAT-006, INV-ING-015 |
| TST-CAT-006 | prop | Facet count equals result count for random filters | INV-CAT-007, INV-DSC-007 |
| TST-CAT-007 | prop | Export rows equal list rows | INV-CAT-008 |
| TST-DSC-001 | prop | Normalizer idempotent; keys stable across versions; folding never lengthens | INV-DSC-002 |
| TST-DSC-002 | gold | Judged query set thresholds; per-class breakdown; regression diff report | INV-DSC-009 |
| TST-DSC-003 | gold | Latin ↔ Bengali alias matching list | INV-DSC-003 |
| TST-DSC-004 | prop | Rebuild from events equals incremental index (result-set equality on random queries) | INV-DSC-005 |
| TST-DSC-005 | prop | Pagination concatenation equals full list under a snapshot | INV-DSC-008 |
| TST-DSC-006 | type+e2e | No code path from `FullDocument` to the indexer (compile-fail test); leak canary: unique string only in non-preview text must never be found | INV-DSC-004 |
| TST-DSC-007 | prop | Bengali collation comparator is a total preorder | INV-DSC-006 |
| TST-DSC-008 | e2e | Unpublish removes from search within 30 s | INV-DSC-001 |
| TST-CAT-009 | e2e | Anonymous gets 404 for Draft/Archived/Deleted books, same as unknown slug | INV-ACC-012 |
