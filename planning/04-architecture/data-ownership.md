# Data ownership

Status: DRAFT

## Rules

1. Exactly one service writes each table. Others read only through the owner's API or events.
2. **No cross-service foreign keys, joins, or shared tables, and no shared volume.** References are opaque typed IDs (`BookId`, `UserId`) validated through APIs or events.
3. Each service has its own PostgreSQL **database** and role in the single `postgres` container (D-24). A service role cannot connect to another service's database (checked in deployment tests).
4. Every table has `created_at`, `updated_at` (UTC); mutable aggregates have `revision bigint` for optimistic concurrency.
5. Audit tables are INSERT-only for service roles (INV-PLT-006).
6. Local copies of foreign data (caches, reading copies) are rebuildable from the owner's API and events.

## Ownership map

| Data | Owner | Copy held elsewhere |
|---|---|---|
| Users, credentials, sessions, TOTP, invites, roles, grants, demo limits, auth audit | identity | none; decisions are requested via `/internal/check`, never copied (grant caches at most 5 s) |
| Books, versions, metadata, publication state, version history, source links | catalog | reader keeps `book_id`, `slug`, `version` with each reading copy; ingestion keeps catalog ids it published |
| Asset files (EPUB, cover) | catalog (own volume) | reader fetches the EPUB by stream and stores only its derived reading copy |
| Shelves ("My Books") | catalog | none; a shelf never grants access |
| Search index (PostgreSQL FTS) | catalog | none |
| Reading copies, reading sessions, progress, bookmarks, highlights, notes | reader (own volume + database) | none |
| Source mirror, intake requests, jobs, curated documents, duplicate reviews, source credential, automation settings | ingestion | none |
| Scrape cache | ingestion (files on its own volume) | none |
| Mail outbox, templates, delivery log | notify | none |
| Audit logs | each service writes its own | none |

## Reference integrity without foreign keys

- A reader copy or ingestion reference to a book is created by an event or API call; when the book is unpublished or deleted, `book.unpublished` marks it and the UI shows "no longer available".
- A nightly reconciliation per service compares its copies with the owner's listing endpoint and reports drift as a metric.
- Deletion is soft (state) in catalog; hard deletion only through an audited retention job.

## Storage classes

| Data | Store | Backup | Retention |
|---|---|---|---|
| Relational | PostgreSQL (`pgdata`) | nightly `pg_dump` per database plus restore drill | per table |
| Catalog assets | volume `catalog_files` | nightly file backup | while a version exists |
| Reading copies | volume `reader_files` | not backed up; regenerable from catalog EPUBs | while published |
| Scrape cache | volume `ingestion_files` | nightly file backup of curated inputs; cache itself regenerable | 90 d for failed, kept for published |
| Secrets/keys | Compose secret files, not in DB | separate encrypted backup | [secrets](../10-security/secrets-and-keys.md) |
