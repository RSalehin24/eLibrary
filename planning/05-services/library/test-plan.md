# library — test plan

Status: DRAFT

| ID | Level | What | Invariant |
|---|---|---|---|
| TST-LIB-001 | model | `Progress.tla` (reordered/duplicated writes) | INV-LIB-001 |
| TST-LIB-002 | prop | Re-anchor on mutated text: whitespace/markup/typo/paragraph-move mutations; ≥ 99% placed for non-semantic changes; never deleted | INV-LIB-002 |
| TST-LIB-003 | prop | `resolve(anchor)` always returns a location or Orphaned | INV-LIB-005 |
| TST-LIB-004 | e2e | Cross-account access: account A cannot read/write B's rows (every route, table-driven) | INV-LIB-003 |
| TST-LIB-005 | db | RLS policies reject cross-owner access even with a handler bug (raw SQL test) | INV-LIB-003 |
| TST-LIB-006 | prop | Shelf PUT twice = once | INV-LIB-004 |
| TST-LIB-007 | prop | Saved filter round-trip | INV-LIB-006 |
| TST-LIB-008 | unit | Notes export contains all and only the owner's annotations | INV-LIB-007 |
| TST-LIB-009 | e2e | Two devices open the same book: single live session per device class; read-once race resolved | INV-LIB-008, INV-ACC-006 |
| TST-LIB-010 | e2e | Failed preparation does not consume read-once opening | INV-ACC-006 |
| TST-LIB-011 | e2e | Artifact set changes: highlights remain; notes page shows orphan state | REQ-LIB-002/005 |
