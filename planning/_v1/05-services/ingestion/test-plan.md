# ingestion — test plan

Status: DRAFT

Existing tests keep their ids; new tests cover the single-pipeline design. Level `gold` uses the gold corpus outside git.

| ID | Level | What | Invariant |
|---|---|---|---|
| TST-ING-001 | model | `JobLifecycle.tla` (leases, fencing epoch, cancel) and `Outbox.tla` checked | INV-ING-006/010/016 |
| TST-ING-002 | prop | Conservation: `blocks_in = blocks_out + blocks_dropped(with reason)` for generated and gold documents | INV-ING-002 |
| TST-ING-003 | prop | Determinism: curate and build twice, shuffled hash seeds, identical document and EPUB bytes | INV-ING-001, INV-CON-002 |
| TST-ING-004 | prop | Order: reading order is a bijection of leaves; nav = TOC = tree | INV-ING-003 |
| TST-ING-005 | gold | Source-TOC fidelity on Type-A books | INV-ING-004 |
| TST-ING-006 | gold | Single-page inference boundaries with evidence | INV-ING-005 |
| TST-ING-007 | prop+model | Completeness: publish impossible when any leaf is unfetched and not `empty_at_source`; mutation test removes a page | INV-ING-006 |
| TST-ING-008 | gold | Entities: per-field precision/recall; nothing auto-published below threshold | INV-ING-007 |
| TST-ING-009 | prop+gold | No duplication across Book Info / Dedication / Front / Body | INV-ING-008 |
| TST-ING-010 | gold | Language: labels follow book language | INV-ING-009 |
| TST-ING-011 | fault | Kill worker at every step boundary and mid-page: request completes once, identical outputs, exactly one catalog version | INV-ING-010/016 |
| TST-ING-012 | gold | Ruleset promotion gate refuses regressions | INV-ING-011 |
| TST-ING-013 | type+review | `SourceClient` exposes only GET; no code path constructs a non-GET; no form submission; allow-list enforced incl. redirects | INV-ING-012 |
| TST-ING-014 | gold | EPUB upload intake of gold EPUBs passes the same validator and build | INV-ING-013 |
| TST-ING-015 | prop | Catalog sync twice: no extra mirror rows or requests; resync never changes request state | INV-ING-014 |
| TST-ING-016 | prop+gold | Duplicate policy on labeled pairs; the matching-rules table is the oracle; volume 1 vs 10, collection vs component, same title different author, missing author, deleted book | INV-ING-015 |
| TST-ING-017 | fault | Source fixtures: 404, 5xx bursts, timeouts, truncated body, locked placeholder, Cloudflare-200 page, redirect loop, huge page: typed outcomes, no hang | REQ-ING-012 |
| TST-ING-018 | drift | Mutated-markup canaries raise `SourceDrift` review, not mass failure | REQ-ING-014 |
| TST-ING-019 | db+prop | Queue: N workers racing never claim the same job (SKIP LOCKED); at most one active job per request; claim order by priority then run_after | INV-ING-010 |
| TST-ING-020 | fault | Lease expiry requeues; zombie executor's late write is rejected by epoch; attempts capped; reaper idempotent | INV-ING-010 |
| TST-ING-021 | prop | Typed errors: retry decision depends only on `JobError` class (message text changes nothing); backoff bounded; `auth_required` parks the request | REQ-ING-010 |
| TST-ING-022 | e2e | Cancel flag: cancel during a 50-page scrape stops within one page, cursor saved, request `cancelled`, retry resumes from cache | REQ-ING-010 |
| TST-ING-023 | e2e | No inline execution: with the worker stopped, every API call returns promptly and work stays queued | REQ-ING-010 |
| TST-ING-024 | prop | Request model: re-sync overwrites only mirror columns; request state unchanged; mirror status equals latest request state | INV-ING-014 |
| TST-ING-025 | e2e | Request actions table-driven over all states x actions: retry, cancel, force-generate (with review and reason), new-edition, resolve-duplicate; illegal pairs return 409 `invalid_transition`; bulk gives per-item results | REQ-ING-010 |
| TST-ING-026 | e2e | Duplicate review: exact_duplicate and needs_review create a pending review and stop; each decision resumes correctly; decision reproduced on reprocess | INV-ING-015 |
| TST-ING-027 | gold+unit | Bengali normalization: exact_key keeps vowel signs (লেখক stays distinct from লখক), punctuation separates words, digits fold, nukta forms equal, ZWJ/ZWNJ removed, loose_key only folds; idempotent; legacy-bug regression (author-role words matched only as whole tokens; "কমল", "বিমল" untouched; "প্রথমা" untouched) | INV-DSC-002, REQ-ING-015 |
| TST-ING-028 | e2e | Credential: states absent/valid/expiring/expired/rejected; secret never in any response or log (canary string); PUT requeues `awaiting_credential` requests | REQ-ING-012 |
| TST-ING-029 | gold | EPUB build: HTML in titles/metadata escaped (injection canary), scripts and handlers removed, images and fonts packaged, OPF metadata complete, epubcheck 0 errors (CI), structure audit 0 errors | INV-CON-007, INV-CON-009 |
| TST-ING-030 | fault | Publish only after build success: audit failure, build crash, catalog down: nothing visible in catalog; catalog intake replay creates one version | INV-ING-016 |
| TST-ING-031 | e2e | Cover rendering sample: no tofu glyphs, contrast >= 4.5:1, title/author legible (visual review) | INV-CON-008 |
| TST-ING-032 | e2e | Automation sequence: due run creates requests within the same run with no idle bounce; failure sets cooldown and does not retry each minute; stop does not retry; missed slots run once; manual and automation runs exclude each other | REQ-ING-014 |
| TST-ING-033 | e2e | Mass-resolve guard: empty, short or failed listing never marks entries missing/resolved and never creates requests | REQ-ING-014 |
| TST-ING-034 | e2e | SSE: events ordered; reconnect with `Last-Event-ID` replays missed events; too-old id yields `reset` then snapshot; slow client dropped without blocking | REQ-ING-010 |
| TST-ING-035 | e2e | Every `/api/ingestion/*` route declares `operate`; reader/demo get 403; mutations audited | INV-ACC |
