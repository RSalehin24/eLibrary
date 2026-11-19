# Data ownership

Status: DRAFT (six services, D-24, D-31, D-33, D-35, D-44)

## Rules

1. Exactly one service writes each table. Others read only through the owner's API or events.
2. **No cross-service foreign keys, joins, or shared tables, and no shared volume.** References are opaque typed IDs (`BookId`, `UserId`) validated through APIs or events.
3. Each service has its own PostgreSQL **database** and role in the single `postgres` container (D-24). A service role cannot connect to another service's database (checked in deployment tests). The gateway has no database.
4. Every table has `created_at`, `updated_at` (UTC); mutable aggregates have `revision bigint` for optimistic concurrency.
5. Audit tables are INSERT-only for service roles (INV-PLT-006); retention 1 year (D-40).
6. Local copies of foreign data (caches, reading copies) are rebuildable from the owner's API and events.

## Ownership map

| Data | Owner | Copy held elsewhere |
|---|---|---|
| Users, credentials, sessions, TOTP, invites, password reset, roles, grants, read-once counters, profile images (D-44), Kindle addresses, auth audit | identity | none; decisions are requested via `/internal/check`, never copied (grant caches at most 5 s, keyed by grant version) |
| Reading tickets (minted and verified) | identity | the reader holds only the `ticket_id` of the one it was given; it verifies each ticket with identity (D-37) |
| Books, versions, metadata, contributors, series, categories, publication state, version history, source links | catalog | reader keeps `book_id`, `slug`, `version` with each reading copy; ingestion keeps catalog ids it published |
| Asset files (EPUB, cover, preview artifact) | catalog (own volume) | reader fetches the EPUB by stream and stores only its derived reading copy; notify streams it for Kindle without storing it |
| Shelves ("My Books"), saved filters (D-43) | catalog | none; a shelf never grants access |
| Search index (PostgreSQL FTS) | catalog | none (derived, rebuildable) |
| Reading copies, reading sessions, progress, bookmarks, highlights, notes, reading ticket audit | reader (own volume + database) | none |
| Reader preferences (theme, font) | reader as the recommendation; **OPEN (O-6)** | none |
| Source mirror, requests, jobs, curated documents, duplicate reviews, source credential status, automation settings | ingestion | none |
| Source credential value (cookie) | a read-only secret file mounted into the ingestion containers; only status and expiry are in the database | none |
| Scrape cache and raw pages | ingestion (files on its own volume) | none |
| Mail outbox, templates, delivery log | notify | catalog stores the Kindle delivery status reported back |
| Audit logs | each service writes its own | none |
| Rate-limit counters | gateway, bounded in memory | none (no cache service) |

## Reference integrity without foreign keys

- A reader copy or ingestion reference to a book is created by an event or API call; when the book is unpublished or deleted, `book.unpublished` marks it and the UI shows "no longer available".
- A scheduled reconciliation per service compares its copies with the owner's listing endpoint (`catalog GET /internal/books`, `reader GET /internal/copies`) and reports drift as a metric; after the outbox drains, drift is zero (REQ-NFR-013).
- Deletion is soft (state) in catalog; hard deletion only through an audited retention job.
- Account deletion: identity removes the account; reader and catalog erase user-owned data (progress, annotations, shelf, saved filters) through a deletion event or internal call (**OPEN, O-1**).

## Storage classes

| Data | Store | Backup | Retention |
|---|---|---|---|
| Relational | PostgreSQL (`pgdata`) | monthly `pg_dump` per database, copied off the host, plus restore drill (D-33; up to 30 days of data may be lost) | per table |
| Profile images (D-44) | volume `identity_files` | monthly file backup | while the account exists |
| Catalog assets | volume `catalog_files` | monthly file backup | while a version exists; previous version until the next is published |
| Reading copies | volume `reader_files` | not backed up; regenerable from catalog EPUBs | while published |
| Scrape cache and raw pages (ingestion files) | volume `ingestion_files` | cache is regenerable; curated inputs with the monthly backup | raw pages 30 d, removed on terminal states |
| Secrets/keys | Compose secret files, not in DB | separate encrypted backup | [secrets](../10-security/secrets-and-keys.md) |
