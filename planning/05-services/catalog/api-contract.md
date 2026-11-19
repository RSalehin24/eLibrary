# catalog - API contract (summary)

Status: DRAFT

The endpoint list is owned by [07-contracts/http/catalog.md](../../07-contracts/http/catalog.md) (31 public routes, 7 internal routes plus health, ready, contract). This page does not repeat it; it records how the service honours the cross-cutting rules.

## Surfaces

| Surface | Routes | Rule |
|---|---|---|
| Public | `/books`, `/books/{slug}`, `/books/{slug}/cover`, `/browse/*` | no session, metadata only (D-34), rate limited at the gateway, `Cache-Control: public, max-age=60` with ETag |
| Signed-in | preview, files, EPUB, Kindle, shelf, saved filters | scopes `preview`, `browse`, `download`, `kindle`; per-book decisions asked from identity; `private, no-store` for downloads |
| Management | `/manage/*` | `manage_catalog`; the only surface showing non-published states and source links |
| Internal | `/internal/*` | service token; ingestion publishes, reader and notify stream the EPUB, notify reports Kindle status, consumers pull events |

## Rules honoured

- **Scope declaration**: every route declares its scope in code; a route without one stops startup (fail closed). Tests: TST-CAT-011.
- **One visibility filter**: reader-facing handlers take `Visible<Book>`; a deleted or non-published book is `404 not_found`, identical to an unknown slug (deny reasons `book_not_published` and `book_deleted` map to 404 for subjects without `manage_catalog`).
- **GET is side-effect free** (REQ-CAT-032): handlers use a read-only connection; the only write on a GET is the audit row of an EPUB download.
- **Concurrency**: `If-Match: <revision>`; stale gives `412 stale_revision`; no merging.
- **Errors**: `validation_failed`, `stale_revision`, `slug_taken`, `no_credit`, `invalid_transition`, `duplicate_saved_filter`, `limit_exceeded`, `kindle_not_available`, `export_too_large`, `conflict`; envelope and statuses in the [error catalog](../../07-contracts/error-catalog.md).
- **Pagination**: keyset with opaque `after` and `snapshot` tokens; default 24, max 100 (provisional, O-7).
- **Idempotency**: `POST /internal/books/{id}/versions` on the build identity `(book_id, build_hash)`; `PUT/DELETE /shelf/{slug}` idempotent; Kindle send on `Idempotency-Key`; status callback on `(request id, status)`.
- **Own data export** (D-55): `GET /me/export` returns shelf entries and saved filters as JSON, session scope, owner only.
- **CSV export**: streamed, same filter and snapshot as the list, cell neutralization for `=`, `+`, `-`, `@`, row cap (provisional 5,000), audited. Scope **OPEN (O-4)**.
- **Files**: never served by Caddy or the gateway; catalog streams after its own scope and state check, with `Range` ([files](files.md)).

## Open items

- C-2: ingestion chooses the book UUID in `POST /internal/books/{id}/versions` (assumed in the contract, not confirmed).
- C-3: `POST /internal/books/match` is kept in the contract but is not in the architecture brief.
- O-4 and O-1 as in the [README](README.md).
