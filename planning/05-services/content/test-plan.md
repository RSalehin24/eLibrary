# content — test plan

Status: DRAFT

| ID | Level | What | Invariant |
|---|---|---|---|
| TST-CON-001 | model | `Publication.tla` | INV-CON-001 |
| TST-CON-002 | db | Attempt UPDATE on Sealed row → rejected; activate non-sealed → rejected; crash between blob write and seal leaves no visible set (fault injection) | INV-CON-001 |
| TST-CON-003 | prop+gold | Build determinism: two builds of the same document are byte-identical (all gold documents) | INV-CON-002 |
| TST-CON-004 | type | Compile-fail: public handler cannot reference `FullDocument`; indexer cannot accept it | INV-CON-003 |
| TST-CON-005 | e2e | Leak canary: unique token placed after the preview cut appears in no public response and no search result | INV-CON-003, INV-DSC-004 |
| TST-CON-006 | e2e | Protected routes reject missing/expired/forged/wrong-book/wrong-action capabilities | INV-CON-004 |
| TST-CON-007 | prop | Range requests: random ranges concatenate to original | INV-CON-005 |
| TST-CON-008 | db+drill | Retention: sets with holds or non-orphaned anchors are not deleted; sweep is two-pass | INV-CON-006 |
| TST-CON-009 | gold | epubcheck 0 errors, structure audit 0 errors, nav = toc on all gold books | INV-CON-007 |
| TST-CON-010 | gold+review | Cover rendering sample: no tofu glyphs, contrast ≥ 4.5:1, title/author legible (visual snapshot review) | INV-CON-008 |
| TST-CON-011 | fuzz | Sanitizer: idempotent; output never contains script, event handlers, external loads, `javascript:` | INV-CON-009 |
