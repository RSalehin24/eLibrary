# Catalog HTTP contract

Status: DRAFT · Service: [catalog](../../05-services/catalog/README.md) · Requirements: [CAT](../../02-requirements/cat-catalog.md) · Conventions: [README](README.md)

Catalog owns books, versions, metadata, contributors (agents), series, categories, publication state, metadata history, source links, assets (EPUB, cover) on its own volume, shelves, saved filters and the PostgreSQL full-text index. Books are identified by UUID and a unique `slug` (D-36); an old slug redirects permanently (`301` with `{redirect_to}`).

Reader-facing routes see only `published`, non-deleted versions by construction (REQ-CAT-002); `/manage/*` is the separate operator surface and the only place source links and non-published states appear. A version is born `published` (D-56; ingestion publishes only gate-passing artifacts in one transaction, no `draft` state). Version states: `published`, `archived` (with `archived_reason` `superseded` or `unpublished`), plus soft delete; there is no approval or rejection state and no approve or reject route (D-49).

## Public API (`/api/catalog`) - 31 routes

### Browse and search (public: metadata only, D-34)

| Method | Path | Scope | Purpose | Errors |
|---|---|---|---|---|
| GET | `/books` | public | list and search. Params: `q` (max 200 chars, Bengali normalization, Latin queries via alias table), facets `writer`, `translator`, `editor`, `publisher`, `series`, `category`, `language` (repeat for OR, distinct for AND), `sort` (`relevance`, `title`, `recent`; Bengali collation for `title`), `after`, `limit` (default 24, max 100), `snapshot`. Response `{items[{id, slug, title, contributors, cover_url, summary, series, categories}], next, snapshot, facets?}`; facet counts equal result counts for the same filter and snapshot | `validation_failed`, `rate_limited` |
| GET | `/books/{slug}` | public | metadata detail of a published book: title, credits with roles, series, categories, publisher, summary, language, cover, `has_preview`; never source URLs or preview text | `not_found` |
| GET | `/books/{slug}/cover` | public | cover image stream (`public, max-age=60`, ETag, nosniff); generated cover when none | `not_found` |
| GET | `/browse/{facet}` | public | facet index (`writers`, `translators`, `editors`, `compilers`, `publishers`, `series`, `categories`) with counts and keyset paging | `not_found` |
| GET | `/browse/{facet}/{id}` | public | books of one writer, series, category, etc.; same response as `/books` | `not_found` |

### Signed-in reader surface

| Method | Path | Scope | Purpose | Errors |
|---|---|---|---|---|
| GET | `/books/{slug}/preview` | preview | the stored `PreviewArtifact`: cover, metadata, summary, TOC, first N characters of the first chapter (N from D-05, 0 allowed); response marks preview text `noindex` (`X-Robots-Tag`) | `not_found`, `forbidden` |
| GET | `/books/{slug}/files` | browse | files tab: available formats, size, whether the caller may download, own Kindle delivery status | `not_found` |
| GET | `/books/{slug}/files/epub` | download | EPUB stream with `Range` support, filename from the slug; audit row | `forbidden`, `not_found` |
| POST | `/books/{slug}/kindle` | kindle | `{address_index}`; creates a Kindle request (published version, size cap, per-user rate limit) and emits `kindle.requested`; 202 with `{request_id}` | `forbidden`, `limit_exceeded`, `kindle_not_available`, `rate_limited` |
| GET | `/books/{slug}/kindle-requests` | kindle | own requests for this book with status (`queued`, `sent`, `failed`, reason) reported back by notify | |
| GET | `/shelf` | browse | "My Books" keyset list; a shelf never grants access | |
| PUT | `/shelf/{slug}` | browse | add (idempotent) | `not_found` |
| DELETE | `/shelf/{slug}` | browse | remove (idempotent) | |
| GET | `/saved-filters` | browse | own saved filters | |
| POST | `/saved-filters` | browse | `{name, query}`; applying a saved filter reproduces the identical query | `duplicate_saved_filter`, `limit_exceeded` |
| DELETE | `/saved-filters/{id}` | browse | delete own | `not_found` |
| GET | `/me/export` | session | the user's own catalog data as JSON: shelf entries and saved filters (D-55); the Settings screen bundles it with the identity and reader exports | |

### Management (`manage_catalog`; session completed TOTP where required)

| Method | Path | Scope | Purpose | Errors |
|---|---|---|---|---|
| GET | `/manage/books` | manage_catalog | operator list across all states (`state`, `q`, facets), paged | |
| GET | `/manage/books/{id}` | manage_catalog | full detail with versions, state, `revision`, source link fields | `not_found` |
| PATCH | `/manage/books/{id}/metadata` | manage_catalog | metadata command with `If-Match: <revision>`: title, credits, series, categories, publisher, summary, `preview_chars`, slug. Operator-owned fields are separate from source-owned ones; a re-import never overwrites an edit; `0` is distinct from null; a published book keeps at least one writer, translator, editor or compiler credit | `stale_revision`, `no_credit`, `slug_taken`, `validation_failed` |
| GET | `/manage/books/{id}/metadata-history` | manage_catalog | metadata version history | |
| GET | `/manage/books/{id}/versions` | manage_catalog | versions with state, build hash, artifact checksums | |
| POST | `/manage/books/{id}/archive` | manage_catalog | unpublish: `published` to `archived(unpublished)` (a manual action; the book is hidden at once); emits `book.unpublished` | `invalid_transition` |
| DELETE | `/manage/books/{id}` | manage_catalog (**OPEN, O-4**) | soft delete (tombstone); files, shelf entries and Kindle requests stop resolving; emits `book.unpublished` | `not_found` |
| GET | `/manage/books/export.csv` | manage_catalog (**OPEN, O-4**) | streamed CSV of the current filtered list (same params as `/manage/books`); cells starting with `=`, `+`, `-`, `@` neutralized, control characters quoted, row cap (provisional 5,000, O-7); audited | `export_too_large` |
| GET | `/manage/books/{id}/source` | manage_catalog | source links (never exposed on reader routes) | |
| GET | `/manage/agents` | manage_catalog | contributors with aliases; `q` search | |
| GET | `/manage/agents/{id}` | manage_catalog | agent, aliases, credits | `not_found` |
| POST | `/manage/agents/{id}/aliases` | manage_catalog | add an alias (Bengali and Latin forms) | `validation_failed` |
| POST | `/manage/agents/merge` | manage_catalog | `{keep_id, merge_ids[]}`; audited, reversible, re-points credits atomically | `conflict` |
| POST | `/manage/agents/{id}/split` | manage_catalog | reverses a merge or separates credits | `invalid_transition` |

There is no manual EPUB upload and no manual physical-book route (D-42, D-01). Publishing is automatic when ingestion's gates pass (D-49); edit, unpublish and delete need `manage_catalog`; `operate` runs the import pipeline only.

## Internal API (`/internal`, service token) - 7 routes

| Method | Path | Caller | Purpose |
|---|---|---|---|
| POST | `/internal/books/{id}/versions` | ingestion | publish a gate-passing build: multipart or staged upload of the EPUB, cover, `PreviewArtifact` and metadata with `{build_hash, source_hash, builder_version}`. Idempotent on the build identity (a retry creates no second version); artifacts accepted atomically; sha256 verified; the version is born `published` in the same transaction (D-56), with no approval step (D-49); a newer version supersedes the older published one and emits `book.version_changed` (`replaced`) only, nothing is rewritten in ingestion; a hash mismatch, missing credit or taken slug returns a typed 4xx (`catalog_rejected` in ingestion) and commits nothing; `id` is the book UUID chosen by ingestion (D-85; creates the book if absent), so a retry with the same `id` and build identity cannot create a duplicate book or version. Size cap 50 MiB |
| GET | `/internal/books/{id}/versions/{version_id}/epub` | reader, notify | stream the EPUB of a version (`Range`), only for published versions or the reader's pending fetch of a just-published version; no scope check beyond the service token and allow-list |
| GET | `/internal/books/{id}` | identity, reader, notify | `{id, slug, title, state, current_version_id, deleted}` for entitlement decisions and Kindle |
| GET | `/internal/books` | reader, ingestion | resync listing: published `{id, slug, version_id, epub_sha256}` keyset-paged (events are a trigger, not the only source) |
| POST | `/internal/books/match` | ingestion | duplicate matching input `{exact_key, authors[], translators[], category, edition}` (a translator difference gives a different book, D-92); returns exact matches and near-matches (listed for a human, never merged) |
| POST | `/internal/kindle-requests/{request_id}/status` | notify | delivery status `{status, error_class?, reason?}` (idempotent by request id and status) |
| GET | `/internal/events` | reader, ingestion | outbox pull: `book.published`, `book.unpublished`, `book.version_changed`, `kindle.requested` (also pulled by notify) |

Also on the internal port: `GET /internal/health`, `GET /internal/ready`, `GET /internal/contract`.

Catalog consumes `user.disabled`, `grant.changed` (and `user.deleted`, OPEN O-1) from identity to invalidate caches and to remove a deleted user's shelf and saved filters.
