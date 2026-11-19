# Legacy data migration

Status: DRAFT · Strategy: [ADR-0013](../../04-architecture/adr/0013-legacy-migration-strategy.md)

## Principles

1. Legacy is read-only input; never modified.
2. Every step is idempotent and keyed by the legacy primary key (stored as `legacy_id` in a `migration_map` table of the target service).
3. Every step produces counts and checksums; a reconciliation report is the exit artifact (INV-MIG-001).
4. Rehearse until the report is empty; cutover is a rerun of the same steps on frozen data.

## Mapping (legacy → new)

| Legacy table / data | Target service & entity | Transformations / risks |
|---|---|---|
| `accounts.User` (email, name, kindle_emails, totp_required, is_active, password hash, otp devices) | identity `Account`, `Credential(legacy_pbkdf2)`, `TotpEnrolment` | status: active→Active, `email_setup_pending`→Invited; TOTP secrets re-encrypted with the new key; demo user flagged; hash format `pbkdf2_sha256$…` verified (INV-MIG-003) |
| `access.PermissionGrant` (12 scopes × targets) | identity `Grant` | scope→action map ([identity domain](../../05-services/identity/domain-model.md)); `read:once`/`read:durable`→Read(mode); `physical_books:view`→`ViewInventory` (if D-01 keeps) else archived; staff/superuser → `Admin` grants + flags |
| `access.BookOpeningRecord` | identity grant (read-once consumption) | 1:1 |
| `catalog.Book` (+ `BookGroup`) | catalog `Book`, `Work` | `BookGroup`→`Work`; books without group → new `Work`; `record_type=physical` → inventory archive (D-01); `review_state`/duplicate-review fields dropped but exported to archive; slug & `catalog_code` preserved verbatim (INV-MIG-002) |
| `catalog.Contributor` (+ roles via `BookContributor`) | catalog `Agent`, `AgentAlias`, `Credit` | **entity cleanup**: run agent dedupe proposals (fuzzy keys) → curator-approved merge list applied during migration, not guessed |
| `catalog.Series`, `Category` (+ joins) | catalog `Series`, `Category` | ordinals kept |
| `Book.main_content_html`, `book_info_html`, `dedication_html`, `toc`, `content_items` | ingestion `DocumentDraft` (as `legacy_import`) + content `CanonicalDocument` | convert to Block IR where possible (re-run stages 2–6 from `raw_scrape_payload`); if raw payload absent, import legacy HTML as sanitized blocks flagged `legacy_build` |
| Generated assets (EPUB/HTML/cover files) | content `Blob`, `ArtifactSet(legacy_build)` | hash, store, seal; rebuild with new builders as a separate, reviewed reprocess (not part of cutover) |
| `ingestion.SourceCatalogEntry`, `BookSubmission`, `ProcessingJob`/logs | ingestion `SourceCatalogEntry`, archived jobs | only entry rows and terminal job summaries; running/queued jobs are re-created after cutover |
| `ingestion.CatalogAutomationSettings`, `processing.ProcessingAutomationSettings` | ingestion `Schedule` | mapped to the three schedule kinds |
| `access.ReadingSession`, `Bookmark`, `Highlight` | library `ReadingSession`(closed), `Progress`, `Bookmark`, `Highlight` | **anchors**: CFI → `Anchor` by locating the highlighted text in the legacy chapter HTML (section id + quote + position); failures become `Orphaned`, never dropped; report the orphan rate |
| `catalog.UserBook` | library `ShelfEntry` | 1:1 |
| `catalog.UserBookKindleSend` | notify `KindleSend`(historic), library view | 1:1 |
| `common.SavedFilter` | library `SavedFilter` | query JSON converted; unknown params dropped with a report |
| `common.AuditLog` | each owner's audit (by action type) or a single `legacy_audit` archive | immutable archive |
| Processing UI projections, caches, Celery state | **not migrated** | derived |

## Steps

1. **Freeze rehearsal copy**: restore legacy backup to an isolated database (never touch production).
2. **Extract** (read-only) to staging files with row counts and per-table checksums.
3. **Load** per target service in dependency order: identity → access → catalog (agents, books) → content (blobs, sets) → library → ingestion → notify.
4. **Verify**: invariants (credit rule, slugs unique, grants map, anchors placement), reconciliation report.
5. **Smoke**: top-100 books readable; 20 random highlights resolve; search finds known books; login with migrated passwords (sampled test accounts).

## Reconciliation report (generated)

| Section | Contents |
|---|---|
| Counts | per entity legacy vs new; explained exclusions listed |
| Checksums | per-table content hash of stable fields; sampled row-level diffs (n=500) |
| Mapping completeness | every legacy PK appears in `migration_map` or in `exclusions.csv` with a reason |
| Quality | agents merged (list), orphaned anchors (count/%), books flagged `legacy_build` (count), grants unmapped (must be 0) |
| Invariants | all INV-CAT/INV-ACC/INV-LIB checks executed against new data |

## Cutover and rollback

Cutover runbook: [cutover](../../11-operations/runbooks/cutover.md). Rollback = proxy switch back to legacy (legacy never altered) until the decommission gate (≥ 30 days of stable operation and a final export archived).
