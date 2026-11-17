# Feature register — keep / change / drop

Status: DRAFT

Every legacy feature gets a disposition. "Requirements" lists where the new
behaviour is specified. Nothing is silently dropped.

| ID | Legacy feature | Disposition | New home | Requirements |
|---|---|---|---|---|
| F-01 | Email login, invite-only accounts | Keep | identity | REQ-IDN-001..006 |
| F-02 | Password create/reset links | Keep | identity + notify | REQ-IDN-002, REQ-NTF-001 |
| F-03 | TOTP 2FA | Keep | identity | REQ-IDN-004 |
| F-04 | Demo auto-login | Change → explicit demo account with limits | identity/access | REQ-IDN-007, REQ-ACC-007 |
| F-05 | 12 permission scopes + grants | Change → typed actions × targets, pure policy | access | REQ-ACC-* |
| F-06 | Read-once / durable read | Keep | access + library | REQ-ACC-006 |
| F-07 | Library list with filters | Change → public search + browse | catalog | REQ-DSC-*, REQ-CAT-007 |
| F-08 | Category/Series/Writer/Translator/Editor/Publisher/Compiler pages | Keep (unified "Agents" and facets) | catalog | REQ-CAT-007 |
| F-09 | Book detail + HTML preview | Change → public book page + build-time preview | catalog + content | REQ-CON-003 |
| F-10 | In-browser reader | Change → chapter-based reader on canonical document | web + content | REQ-CON-004, REQ-WEB-* |
| F-11 | EPUB download | Keep | content | REQ-CON-004 |
| F-12 | Send to Kindle + sent history | Keep | notify + library | REQ-NTF-002 |
| F-13 | Bookmarks, highlights, notes page | Keep, re-anchor on rebuild | library | REQ-LIB-002, REQ-LIB-005 |
| F-14 | Reading progress | Keep | library | REQ-LIB-001 |
| F-15 | Saved filters | Keep | library | REQ-LIB-006 |
| F-16 | My Books (created by me) | Keep | library | REQ-LIB-004 |
| F-17 | Submit source URL → create book | Keep | ingestion | REQ-ING-* |
| F-18 | Catalog sync from source archive | Keep | ingestion | REQ-ING-014 |
| F-19 | Incomplete-book checks / auto-retry | Change → completeness proof + review queue | ingestion | REQ-ING-006 |
| F-20 | Multi-page TOC processing page | Drop as a page (algorithmic concern, not UI) | ingestion | REQ-ING-004 |
| F-21 | On-hold / failed / duplicate review pages | Change → single Review queue | ingestion + web | REQ-ING-007, REQ-WEB-008 |
| F-22 | Reprocessing page | Change → reprocess with diff preview | ingestion | REQ-ING-011 |
| F-23 | Force Generate on REVIEW_REQUIRED | Drop (replaced by explicit resolution actions in Review) | ingestion | REQ-ING-007 |
| F-24 | Manual EPUB intake | Keep | ingestion | REQ-ING-013 |
| F-25 | Metadata editing, contributor validation | Change → overrides + merge/split | catalog | REQ-CAT-004, REQ-CAT-005 |
| F-26 | Duplicate detection, "new edition" | Keep, one implementation | ingestion + catalog | REQ-ING-015, REQ-CAT-006 |
| F-27 | Book/ticket exports CSV/XLSX/PDF | Keep | catalog | REQ-CAT-008 |
| F-28 | Physical books list / manual books / binding, price | **OPEN D-01** | catalog (module) | REQ-CAT-009 |
| F-29 | Audit log | Keep, append-only | platform | REQ-PLT-006 |
| F-30 | Dark mode | Keep, plus sepia | web | REQ-WEB-006 |
| F-31 | Health, CSRF endpoints | Keep | gateway | REQ-GWY-002 |
| F-32 | Migration / deploy / log scripts | Rebuild | operations | REQ-PLT-008 |
