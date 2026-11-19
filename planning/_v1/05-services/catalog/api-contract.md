# catalog — API contract

Status: DRAFT · Source of truth: `contracts-catalog`

Prefix `/api/catalog` (public listener via caddy) and `/internal` (service network, internal service token, never routed by caddy). Every route declares its scope in code; an undeclared route fails startup. Caddy forward-auth supplies `X-User-Id` and `X-Scopes`; the service trusts them only from caddy. Mutations require `If-Match: <revision>` where a revision exists.

## Public (scope `browse` or `preview`; no session)

| Method and path | Scope | Response | Notes |
|---|---|---|---|
| `GET /api/catalog/search?q&category&writer&series&language&sort&after&limit` | public/browse | `{items[], next_after, total}` | keyset; `q` length <= 200, limit <= 50, rate limited per IP; only visible books |
| `GET /api/catalog/books?...same filters...` | public/browse | list | same facet semantics as search (AND across, OR within) |
| `GET /api/catalog/books/{slug}` | public/browse | book detail (metadata, credits, series, categories, `files` summary, `viewer` abilities when a session exists) | 301 to current slug for old slugs; Draft, in-review, archived, deleted = 404 same as unknown |
| `GET /api/catalog/books/{slug}/preview` | public/preview | `{html, policy_hash}` sanitized preview | D-12 |
| `GET /api/catalog/books/{slug}/cover` | public/browse | image, `ETag: <sha256>`, `Cache-Control: public, immutable` | |
| `GET /api/catalog/agents?role&q&after`, `GET /api/catalog/agents/{code}` | public/browse | writer, translator, editor, publisher pages | counts equal displayed results |
| `GET /api/catalog/categories`, `/series`, `/series/{id}` | public/browse | taxonomy, series ordered | |

## Signed-in (session required)

| Method and path | Scope | Response | Notes |
|---|---|---|---|
| `GET /api/catalog/books/{slug}/download` | `download` (grant for this book or global) | EPUB stream, `Content-Disposition: attachment`, `Accept-Ranges: bytes` | scope checked with identity `/internal/check`; logs `download_log` |
| `POST /api/catalog/books/{slug}/kindle` | `kindle` | `202 {request_id}` | `Idempotency-Key` header; address taken from identity profile; size and daily limits; writes `kindle_requests` and event `kindle.requested` in one transaction |
| `GET /api/catalog/shelves`, `GET /api/catalog/shelves/{id}/items?after` | `browse` | shelves and items (visible books only) | |
| `PUT /api/catalog/shelves/my-books/items/{book_id}`, `DELETE ...` | `browse` (mutation; identity refuses mutations for role demo) | `204` | shelf only; never grants access |
| `POST /api/catalog/shelves`, `PATCH`/`DELETE /api/catalog/shelves/{id}` | `browse` (mutation) | custom shelves | |

## Management (scope `manage_catalog`)

| Method and path | Response | Notes |
|---|---|---|
| `GET /api/catalog/admin/books?state&q&source&deleted&after` | list incl. all states | |
| `GET /api/catalog/admin/books/{id}` , `GET .../versions` | detail, version list with state and asset summary | |
| `PATCH /api/catalog/admin/books/{id}/metadata` | new `revision` | field-level override with `If-Match`; stale revision = 412 `stale_revision`; writes `metadata_revisions` |
| `GET /api/catalog/admin/books/{id}/history`, `POST .../history/{rev}/restore` | revision list; restore writes a new revision | |
| `POST /api/catalog/admin/versions/{vid}/submit` | draft to `in_review` | manual path; ingestion versions arrive already `in_review` |
| `POST /api/catalog/admin/versions/{vid}/approve` | `in_review` to `published` | requires assets verified and credit rule; previous published version becomes `archived`; emits `book.published` (and `book.version_changed` if a version was replaced) |
| `POST /api/catalog/admin/versions/{vid}/reject` `{reason}` | back to `draft`, review `rejected` | emits `book.version_changed` |
| `POST /api/catalog/admin/books/{id}/archive` , `/restore` | published to archived; archived to published | emits `book.unpublished` / `book.published` |
| `DELETE /api/catalog/admin/books/{id}` , `POST .../undelete` | soft delete; undelete within retention | removes search doc; emits `book.unpublished` |
| `POST /api/catalog/admin/agents/merge`, `POST .../agents/{id}/split`, `POST .../books/{id}/link-edition` | audited, reversible | preview of affected credits via `?dry_run=true` |
| `GET /api/catalog/admin/export.csv?filter...` | streamed CSV, row cap, CSV escaping | exactly the rows of the filtered list (INV-CAT-008) |
| `GET /api/catalog/admin/audit?after` | audit rows | |

## Internal (service token)

| Method and path | Caller | Purpose |
|---|---|---|
| `PUT /internal/books/by-source/{source_key}` | ingestion | find or create the book shell (no version, invisible); returns `{book_id, code, slug, has_published}`; idempotent |
| `POST /internal/books/{id}/versions` | ingestion | multipart: `metadata` (JSON: title, language, credits, series, categories, edition, summary, `forced`, `ingestion_request_id`), `epub`, `cover?`, `preview`; header `Idempotency-Key = build_hash`; streams files into the blob store, verifies EPUB zip and image magic, re-sanitizes preview; creates the version as `in_review` and an `open` review; `201 {version_id, version_no, state}`; replay returns the same body with `200` |
| `POST /internal/duplicates/classify` | ingestion | input `{title_key, author_keys[], translator_keys[], category_keys[], publisher_key?, edition_label?, series?, source_key}`; output `{class, candidates[{book_id, evidence}]}` with class in ExactDuplicate, NewEdition, NewTranslation, NewWork, NeedsReview; pure and deterministic over catalog rows; never auto-creates; matches deleted books as NeedsReview (`matches_deleted_book`) |
| `POST /internal/agents/resolve` | ingestion | candidates with exact/alias evidence for raw names; no auto-create |
| `GET /internal/books/{id}/versions/{v}/epub` | reader, notify | EPUB stream with Range; logged as `reader_internal` / `kindle_internal`; only for `published` versions (404 otherwise, except the version a `kindle.requested` event names) |
| `GET /internal/books/{id}/facts` | reader, identity | `{state, published_version, slug, title, language}` |
| `GET /internal/events?after=<cursor>&limit` | reader, ingestion, notify | outbox page `{events[], next}`; at-least-once, ordered by id |
| `GET /internal/health` , `GET /internal/contract` | all | liveness/readiness, contract version |

## Error model

All errors: `{"error": {"code": "...", "message": "...", "request_id": "...", "details": {}}}`, `Content-Type: application/json`.

| HTTP | `code` | When |
|---|---|---|
| 400 | `invalid_request` , `invalid_file` , `invalid_epub` | validation, bad magic bytes, zip structure |
| 401 | `unauthenticated` | no session on a signed-in route |
| 403 | `forbidden` , `scope_missing` | scope or grant absent |
| 404 | `not_found` | unknown or not visible (indistinguishable) |
| 409 | `invalid_transition` , `credit_rule_failed` , `asset_missing` , `duplicate_slug` | state machine or constraint refusal; `details.allowed` lists legal transitions |
| 412 | `stale_revision` | `If-Match` mismatch |
| 413 | `too_large` | upload or Kindle size cap |
| 429 | `rate_limited` | `Retry-After` set |
| 503 | `dependency_unavailable` | identity check unreachable (fail closed for scoped routes; public routes unaffected) |

## Behavior guarantees

- Public GETs: `ETag`, `Cache-Control: public, max-age=60, stale-while-revalidate=300`; authenticated responses `private, no-store`.
- Unpublish removes a book from search and public routes in the same transaction as the state change (INV-DSC-001), so the 30 s budget of REQ-DSC-005 is met by construction.
- Internal intake is idempotent on `(book_id, build_hash)`; a retry never creates a second version.
