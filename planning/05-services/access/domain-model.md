# access — domain model

Status: DRAFT

## Actions (closed enum, replaces the 12 legacy scopes)

| Action | Meaning | Legacy scope |
|---|---|---|
| `Search`, `ViewMetadata`, `ViewPreview` | Public discovery | (login-only before) |
| `Read` | Full text via reader | `read:durable`, `read:once` |
| `Download` | EPUB download | `download:file` |
| `SendToKindle` | Kindle delivery | `send:kindle` |
| `Submit` | Start book creation | `submit:create` |
| `EditMetadata` | Edit catalog data | `metadata:edit` |
| `ManageIngestion` | Sources/Jobs/Review | `processing:manage` |
| `ViewSourceRecords` | See source URLs/raw records | `source_records:view` |
| `ManageAccess` | Grants and accounts | `access:manage` |
| `ViewInventory` | Physical list (deferred to v1.1, D-01; action reserved) | `physical_books:view` |
| `Admin` | All of the above | `admin:full_control` |

`Read` carries a mode: `Durable` or `Once`. `Once` grants are limited by openings.

## Targets

`Global` · `Category(id)` · `Agent(id)` (as writer) · `Book(id)`. A grant covers a book when its target matches (category membership and authorship come from the `book_facts` projection fed by catalog events).

## Entities

| Entity | Fields |
|---|---|
| `Grant` | `id`, `account_id`, `action`, `mode?`, `target`, `starts_at`, `expires_at?`, `revoked_at?`, `granted_by`, `reason`, `revision` |
| `DefaultPolicy` | versioned set of grants applied to every Active non-demo account (decision D-04) |
| `DemoPolicy` | explicit allowlist for demo subjects |
| `Opening` | `(account_id, book_id)` unique, `consumed_at`, `session_id` |
| `subject_facts` (projection) | `account_id, active, totp_required, demo, mfa_ok_sessions` |
| `book_facts` (projection) | `book_id, state, category_ids, writer_ids` |
| `AuditEntry` | INSERT-only |
| `SigningKey` | `kid`, `public`, `private_ref`, `not_before`, `not_after` |

## Resolution order (documented, then proven order-independent)

`decide` computes the union of all live applicable grants (explicit + default policy); it is
a set union, so order cannot matter (INV-ACC-010). There are no deny-grants in v1; revoking
is deleting effect by `revoked_at`. (Deny rules are a deliberate non-feature: they break monotonicity.)
