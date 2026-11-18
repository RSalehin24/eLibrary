# reader - test plan

Status: DRAFT

| ID | Level | What | Maps to |
|---|---|---|---|
| TST-RDR-001 | model | `Progress.tla` (reordered/duplicated writes) | INV-LIB-001 |
| TST-RDR-002 | unit | Package build: OPF, spine, TOC, images, fonts from fixture EPUBs; Bengali content preserved; build is deterministic for identical input | brief 5.1 (REQ-CON-002 reading part) |
| TST-RDR-003 | prop+fuzz | Sanitizer: no script, handler, external load, `javascript:`/`data:` link survives; links and resources rewritten to package ids; no panic on hostile XHTML | REQ-CON-009 |
| TST-RDR-004 | e2e | Open -> ticket (body) -> redeem with header; ticket in a URL query is rejected and never logged | brief 5.2/5.3 |
| TST-RDR-005 | unit | Ticket TTL is 15 min with fake clock (valid at 14:59, invalid at 15:00); bound to user, book, version; wrong user/book/version rejected | brief 5.2 |
| TST-RDR-006 | e2e | Whole book is returned by one `GET /book` response; no per-chapter content route exists; EPUB file route absent on reader | brief 5.3 |
| TST-RDR-007 | e2e | Read-once: open does not consume; redeem consumes once; reload with same ticket works; new ticket denied; missing copy or `building` state never consumes | INV-ACC-006, brief 5.4 |
| TST-RDR-008 | e2e | Two devices race to redeem a read-once book: exactly one consumes the use, the other is denied | INV-ACC-006 |
| TST-RDR-009 | e2e | Revocation: `grant.changed`, `user.disabled`, `book.unpublished` make the next redeem/refresh fail | brief section 7 (reader token row) |
| TST-RDR-010 | e2e | Unpublished/draft/withdrawn book: open returns `not_found`; stale ticket after unpublish fails | INV-ACC-012 |
| TST-RDR-011 | e2e | Cross-account: A cannot read or change B's progress, bookmarks, highlights (table-driven over all routes); other owners' ids give 404 | INV-LIB-003 |
| TST-RDR-012 | db | RLS rejects cross-owner SQL even with a handler bug | INV-LIB-003 |
| TST-RDR-013 | e2e | Bookmark create twice -> one row (200 on repeat); delete twice -> 204; delete works without a ticket | brief 5.6 |
| TST-RDR-014 | prop | Progress: stale revision never overwrites; percent bounded 0..100 | INV-LIB-001 |
| TST-RDR-015 | prop | Quote re-anchoring on mutated text (whitespace, markup, small edits): placed or reported unplaced, never deleted | INV-LIB-002 |
| TST-RDR-016 | e2e | Notes page links open the exact chapter and offset, or show unplaced state | REQ-LIB-005 |
| TST-RDR-017 | unit | Notes export has all and only the owner's annotations (md and json) | INV-LIB-007 |
| TST-RDR-018 | e2e | Demo user: can open the demo set, cannot write state (403 `forbidden_demo`), cannot open non-demo books | INV-ACC-007 |
| TST-RDR-019 | contract | Event consumer: duplicate and replayed events leave state unchanged; crash between effect and cursor re-applies safely (cursor and effect in one transaction) | brief section 3 |
| TST-RDR-020 | fault | Catalog unreachable during build: retries, `copy_unavailable` on open, nothing served half-built; rebuild succeeds later | brief 5.1 |
| TST-RDR-021 | e2e | Open audit: every open/redeem/denied writes an `opens` row without the ticket secret | brief 5 (honest limit, audit) |
| TST-RDR-022 | e2e | Rate limits: open and progress limits enforced with `429` and `Retry-After` | brief 5.5 |
| TST-RDR-023 | doc | Honest-limit statement present in README, API docs and in-app help | brief 5.5 |
