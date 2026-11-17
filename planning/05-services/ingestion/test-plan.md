# ingestion — test plan

Status: DRAFT

| ID | Level | What | Invariant |
|---|---|---|---|
| TST-ING-001 | model | `JobLifecycle.tla` and `Outbox.tla` checked | INV-ING-006/010/016 |
| TST-ING-002 | prop | **Conservation**: for random HTML documents (generator) and every gold document, `blocks_in = blocks_out + blocks_dropped(with reason)` as multisets | INV-ING-002 |
| TST-ING-003 | prop | **Determinism**: pipeline run twice and with shuffled hash-map seeds gives identical canonical document bytes | INV-ING-001, INV-CON-002 |
| TST-ING-004 | prop | **Order**: reading order is a bijection of leaves; nav links = TOC links = tree | INV-ING-003 |
| TST-ING-005 | gold | **Source-TOC fidelity**: tree shape/titles equal source TOC for all Type-A gold books | INV-ING-004 |
| TST-ING-006 | gold | **Single-page inference**: boundary precision/recall ≥ targets; each boundary has evidence | INV-ING-005 |
| TST-ING-007 | prop+model | **Completeness**: publish impossible when any leaf is unfetched; mutation test removes a page from a fixture | INV-ING-006 |
| TST-ING-008 | gold | **Entities**: per-field precision/recall/F1 vs targets; no auto-published entity below threshold | INV-ING-007 |
| TST-ING-009 | prop+gold | **No duplication** across Book Info / Dedication / Front / Body | INV-ING-008 |
| TST-ING-010 | gold | **Language**: labels follow book language (bn, en, mixed) | INV-ING-009 |
| TST-ING-011 | fault | Kill worker at each step (every cut point); job completes once with identical outputs; no double publish | INV-ING-010/016 |
| TST-ING-012 | gold | Ruleset promotion gate refuses regressions (inject a worse ruleset → gate fails) | INV-ING-011 |
| TST-ING-013 | type+review | Acquisition client exposes only GET; no code path constructs non-GET | INV-ING-012 |
| TST-ING-014 | gold | Manual EPUB intake of gold EPUBs yields documents passing the same validator | INV-ING-013 |
| TST-ING-015 | prop | Catalog sync twice → no extra jobs/entries | INV-ING-014 |
| TST-ING-016 | prop+gold | Duplicate policy on labeled pairs; table-driven all five cases + boundary cases | INV-ING-015 |
| TST-ING-017 | fault | Source fixtures: 404 chapter, 5xx bursts, timeouts, truncated body, locked placeholder, redirect loop, huge page → typed outcomes, no hang | REQ-ING-012 |
| TST-ING-018 | drift | Canary fixtures with mutated markup → `SourceDrift` review, not mass failure | REQ-ING-014 |
