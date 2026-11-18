# catalog — domain model

Status: DRAFT

PostgreSQL schema `catalog`, role `catalog`. Files on volume `/data/catalog` (not shared with other services). UUIDs are v4 unless noted; all timestamps `timestamptz`.

## Identity and publication

| Table | Columns | Keys / constraints / indexes |
|---|---|---|
| `works` | `id`, `canonical_title`, `original_language`, `created_at` | groups editions and translations (replaces legacy `BookGroup`); optional for a book |
| `books` | `id`, `work_id?`, `code` (stable public code), `slug`, `source_key?` (hash of the canonical source URL), `published_version_id?`, `latest_version_id?`, `deleted_at?`, `deleted_by?`, `revision` (int), `created_at` | PK `id`; `UNIQUE(code)`; `UNIQUE(slug)`; `UNIQUE(source_key)` where not null; FK `published_version_id` and `latest_version_id` to `book_versions` (deferrable); `code` and `id` immutable (trigger rejects UPDATE) (INV-CAT-003) |
| `book_versions` | `id`, `book_id`, `version_no`, `state` (`draft`\|`in_review`\|`published`\|`archived`), `title`, `subtitle?`, `language`, `edition_label?`, `publisher_agent_id?`, `first_published?`, `summary?`, `forced` (bool), `ingestion_request_id?`, `build_hash`, `created_by` (account or `ingestion`), `created_at`, `state_changed_at`, `rejected_reason?` | `UNIQUE(book_id, version_no)`; `UNIQUE(book_id, build_hash)` (makes intake idempotent); partial `UNIQUE(book_id) WHERE state='published'` (at most one published version); CHECK: `state='published'` requires an `epub` asset and a credit with role in {writer, translator, editor, compiler} (trigger at transition) (INV-CAT-002); versions are append-only except `state*`, `summary`, metadata columns while `draft`/`in_review` |
| `book_slugs` | `slug`, `book_id`, `created_at` | PK `slug`; every former and current slug; old slug answers 301 |
| `book_sources` | `book_id`, `source_url`, `source_key`, `first_linked_at` | `UNIQUE(source_key)`; used by ingestion duplicate check stage 1 |

Visible to the public iff `books.published_version_id IS NOT NULL AND books.deleted_at IS NULL`. The two columns are only changed inside the transitions in [state machines](state-machines.md).

## Metadata (per version) and history

| Table | Columns | Constraints |
|---|---|---|
| `agents` | `id`, `kind` (`person`\|`organization`), `display_name`, `code`, `exact_key`, `merged_into?`, `revision` | `UNIQUE(code)`; identity is the id only (INV-CAT-005) |
| `agent_aliases` | `agent_id`, `alias`, `script` (`bengali`\|`latin`), `exact_key`, `loose_key` | `UNIQUE(exact_key, agent_id)`; feeds search (REQ-DSC-003) |
| `credits` | `version_id`, `agent_id?`, `raw_name?`, `role` (writer, translator, editor, compiler, illustrator, cover_artist, publisher), `ordinal` | PK `(version_id, role, ordinal)`; `agent_id` or `raw_name` present; unresolved `raw_name` becomes an agent on approval (exact-key dedupe) |
| `series` , `version_series` | `series(id, name, exact_key)` ; `version_series(version_id, series_id, ordinal numeric?)` | `UNIQUE(series_id, ordinal)` per published version when ordinal present |
| `categories`, `version_categories` | `categories(id, code, name, exact_key, parent_id?)` ; join on `(version_id, category_id)` | tree depth <= 3, acyclic |
| `field_overrides` | `book_id`, `field`, `value`, `set_by`, `set_at`, `source_value_hash`, `stale` (bool) | PK `(book_id, field)`; override wins over any source value; `stale` set when a new ingested version changes the source value (INV-CAT-004) |
| `metadata_revisions` | `id` (bigserial), `book_id`, `version_id`, `revision_no`, `source` (`ingestion`\|`admin`), `changed_by`, `changed_at`, `changes` (jsonb: field to [old,new]), `snapshot` (jsonb) | `UNIQUE(book_id, revision_no)`; append-only (REVOKE UPDATE/DELETE); restoring writes a new revision, never rewrites history |
| `metadata_reviews` | `id`, `version_id`, `state` (`open`\|`approved`\|`rejected`), `requested_by`, `decided_by?`, `decided_at?`, `note?` | partial `UNIQUE(version_id) WHERE state='open'`; created when a version enters `in_review` |
| `agent_merges` | `from_agent`, `into_agent`, `moved_credits` (jsonb), `at`, `by` | enables split/undo |

Provenance: every revision row says whether the change came from `ingestion` (with `ingestion_request_id` on the version) or from an `admin`. Re-ingestion creates a new version; overrides stay and are flagged `stale` when their source value changes.

## Assets (former content service)

| Table | Columns | Constraints |
|---|---|---|
| `assets` | `id`, `version_id`, `kind` (`epub`\|`cover`\|`preview`), `sha256`, `size_bytes`, `media_type`, `storage_path` (relative, derived from hash), `created_at` | `UNIQUE(version_id, kind)`; write-once (trigger rejects UPDATE/DELETE except by the purge job); `kind='epub'` is `application/epub+zip` verified by magic bytes and a ZIP structure check; cover is a verified raster image, <= size cap; `preview` is sanitized HTML produced by ingestion from the allow-list (metadata, summary, TOC, first N characters of the first chapter) and re-sanitized on intake (INV-CON-003, INV-CON-009) |

Storage layout: `/data/catalog/blobs/ab/cd/<sha256>`; written to a temp file, hashed, fsynced, renamed; the row is inserted in the same request after the rename. A blob without a row is orphan-swept after 24 h; a row whose blob is missing or fails its hash blocks `approve` and is reported by the nightly verify job.

## Shelves, Kindle, downloads

| Table | Columns | Constraints |
|---|---|---|
| `shelves` | `id`, `user_id`, `name`, `kind` (`my_books`\|`custom`), `created_at` | `UNIQUE(user_id, name)`; one `my_books` per user (partial unique); a shelf never grants access (X3) |
| `shelf_items` | `shelf_id`, `book_id`, `added_at` | PK `(shelf_id, book_id)`; may reference non-visible books (hidden from reads) |
| `kindle_requests` | `id`, `user_id`, `book_id`, `version_id`, `asset_id`, `to_address`, `requested_at`, `state` (`issued`\|`rejected_limit`), `idempotency_key` | `UNIQUE(user_id, idempotency_key)`; catalog only records issuance; delivery result is in notify |
| `download_log` | `id`, `user_id`, `book_id`, `version_id`, `at`, `kind` (`download`\|`kindle_internal`\|`reader_internal`) | INSERT-only; feeds audit and rate limits |

## Search

| Table | Columns | Constraints |
|---|---|---|
| `search_docs` | `book_id` (PK), `version_id`, `doc` (tsvector, config `simple`), `title_sort`, `title_exact_key`, `code`, `facet_categories int[]`, `facet_writers int[]`, `facet_series int[]`, `language`, `published_at` | GIN on `doc`; btree on `(title_sort, book_id)` and `(published_at, book_id)`; GIN on facet arrays; row exists iff the book is publicly visible; updated in the same transaction as `published_version_id` |

Weights: A title and subtitle, B contributor names and aliases (loose key), C series, category, code, D preview text. Text is normalized by the shared `bn-text` function (see ingestion domain model, "Bengali normalization"); the same function version is stored in `search_meta.normalizer_version`; a mismatch triggers a rebuild. Only metadata and the preview asset are indexed (INV-DSC-004): the indexer takes a `PublicDocument` value that cannot hold other text.

## Events and cursors

| Table | Columns | Notes |
|---|---|---|
| `events` | `id` (bigserial), `type`, `book_id`, `version_id?`, `payload` (jsonb), `created_at` | written in the same transaction as the change; payload carries `book_id`, `slug`, `version_id`, `version_no`, `epub_sha256`; consumers use `id` as cursor; retained 30 days |
| `event_cursors` | `source` (PK), `last_id` | catalog's cursors into identity's events |
| `audit_log` | `id`, `actor`, `action`, `target`, `at`, `details` | INSERT-only; all admin transitions, overrides, deletes, exports |

## Value types

`Sha256`, `Slug`, `BookCode`, `SafeHtml` (sanitizer output, idempotent), `PublicDocument` (metadata plus preview only), `VersionState` (enum, transitions only through `Version<S>` methods), `Revision`.
