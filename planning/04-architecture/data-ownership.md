# Data ownership

Status: DRAFT

## Rules

1. Exactly one service writes each table. Others read only through the owner's API or events.
2. **No cross-service foreign keys, joins, or shared tables.** References are opaque typed IDs (`BookId`, `AccountId`) validated through events/APIs.
3. Each service has its own PostgreSQL **database** and role (v1: one server, separate databases). A service role cannot connect to another service's database (checked in deployment tests).
4. Every table has `created_at`, `updated_at` (UTC), and mutable aggregates have `revision bigint` for optimistic concurrency.
5. Audit tables are INSERT-only for service roles (INV-PLT-006).
6. Local projections of foreign data are rebuildable from events and marked `*_projection`.

## Ownership map

| Data | Owner | Replicated as projection in |
|---|---|---|
| Account (id, email, status, display name) | identity | access (`subject_facts`), notify (mail address cache), library (display only) |
| Grants, default policy, openings | access | — (decisions are requested, never copied) |
| Book, Work, Agent, Credit, Series, Category | catalog | ingestion (`catalog_refs` for duplicate checks), library (`book_refs`: id, slug, title) |
| Search index | catalog | — |
| Artifact sets, canonical documents (published) | content | library (`section_index` per artifact set, for anchors) |
| Snapshots, jobs, drafts, review items, rulesets | ingestion | — |
| Progress, annotations, shelf, saved filters | library | — |
| Mail log, Kindle log | notify | library (`kindle_sent` view for the "sent" page) |
| Audit log | each service writes its own; platform `audit` reader aggregates | — |

## Reference integrity without foreign keys

- A projection row is created by the corresponding event; if the referenced entity is later deleted, a tombstone event marks the projection and dependent UI shows "no longer available".
- Reconciliation job (nightly, per service) compares projections with the owner's listing endpoint and emits metrics `projection_drift_total`; non-zero pages the operator.
- Deletion is soft (state) in catalog; hard deletion only through an audited retention job.

## Storage classes

| Data | Store | Backup | Retention |
|---|---|---|---|
| Relational | PostgreSQL | continuous WAL + daily base | per table, see service domain models |
| Artifacts, snapshots | content-addressed file store (`sha256/ab/cd/…`), path layout fixed | daily rsync/restic to offsite | artifacts: while referenced + 30 d; snapshots: forever for published books, 90 d for failed |
| Secrets/keys | environment / secret file, not in DB | separate encrypted backup | rotation per [security](../10-security/secrets-and-keys.md) |
