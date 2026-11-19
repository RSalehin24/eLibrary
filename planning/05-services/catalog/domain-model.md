# catalog - domain model

Status: DRAFT (rewritten: no works table, no catalog code, no demo; D-31, D-36, D-42, D-43)

PostgreSQL database `catalog`, role `catalog`. Files on volume `/data/catalog` (not shared). UUIDv4 unless noted; all timestamps `timestamptz` UTC; mutable aggregates carry `revision bigint` ([data ownership](../../04-architecture/data-ownership.md)). No cross-service foreign keys: `user_id` columns are opaque ids.

## Entities and value types

| Type | Meaning | Invariant |
|---|---|---|
| `Book` | identity of a book: immutable `id`, current `slug`, pointer to the current published version, tombstone | INV-CAT-005, 003 |
| `BookVersion` | one immutable build of the book (metadata snapshot plus assets) with a state | INV-CAT-001, 021 |
| `Agent`, `Alias` | a contributor and its spellings; identity is the id only | INV-CAT-007 |
| `Credit` | (version, role, agent, ordinal) | INV-CAT-004, 007 |
| `Series`, `Category` | ordered series, category tree (depth <= 3) | INV-CAT-008 |
| `Asset` | write-once file: `epub`, `cover`, `preview` | INV-CAT-020, 021 |
| `ShelfEntry` | (user, book), never an access decision | INV-CAT-025 |
| `SavedFilter` | per-user named query JSON | INV-CAT-026, 033 |
| `KindleRequest` | request issued plus status reported by notify | INV-CAT-029 |
| `Slug`, `Sha256`, `Revision` | validated newtypes | INV-CAT-005 |
| `PublicDocument` | the only input of the search indexer and public detail: metadata, cover reference, summary; no preview text (D-34), no source URL, no user data | INV-CAT-012 |
| `PreviewArtifact` | stored preview (TOC, first N characters) served only to `preview` | INV-CAT-019 |
| `Visible<Book>` | produced only by the single `visible_books` repository filter; reader-facing handlers accept only this | INV-CAT-002, 003 |
| `VersionState` | enum; transitions only through consuming methods (`Version<Published>::archive`; a version is constructed `published` by intake, D-56) | INV-CAT-001 |

Visibility: a book is publicly visible iff `books.current_version_id IS NOT NULL AND books.deleted_at IS NULL`. Both columns change only inside the transitions of [state machines](state-machines.md).

## Tables: books and versions

| Table | Columns | Keys, constraints, indexes |
|---|---|---|
| `books` | `id`, `slug`, `current_version_id?`, `latest_version_id?`, `source_key?` (hash of the canonical source URL), `deleted_at?`, `deleted_by?`, `revision`, `created_at`, `updated_at` | PK `id`; `UNIQUE(slug)`; `UNIQUE(source_key)` where not null; `id` immutable (trigger rejects UPDATE of `id`); FKs to `book_versions` deferrable. INV-CAT-003, 005 |
| `book_slugs` | `slug` (PK), `book_id`, `created_at` | every former and current slug; an old slug answers `301 {redirect_to}` permanently; a slug is never reused by another book. INV-CAT-005 |
| `book_versions` | `id`, `book_id`, `version_no`, `state` (`published` \| `archived`; born `published`, D-56), `archived_reason?` (`superseded` \| `unpublished`), `title`, `subtitle?`, `language`, `edition_label?`, `publisher_agent_id?`, `first_published?`, `summary?`, `preview_chars` (int, 0 allowed), `build_hash`, `source_hash`, `builder_version`, `ingestion_request_id?`, `created_by`, `created_at`, `state_changed_at` | `UNIQUE(book_id, version_no)`; `UNIQUE(book_id, build_hash)` (idempotent intake, INV-CAT-022); partial `UNIQUE(book_id) WHERE state='published'`; `CHECK(state <> 'archived' OR archived_reason IS NOT NULL)`; trigger at `published`: an `epub` asset exists, hash verified, and at least one credit with role in {writer, translator, editor, compiler} (INV-CAT-004); rows are append-only except state columns and metadata columns while `draft` (the in-transaction intake state, INV-CAT-021) |
| `book_sources` | `book_id`, `source_url`, `source_key`, `first_linked_at` | `UNIQUE(source_key)`; read only on `/manage/*` and by `books/match`; the reader-facing view type has no field for it (INV-CAT-002) |

## Tables: metadata, agents, history

| Table | Columns | Constraints |
|---|---|---|
| `agents` | `id`, `kind` (`person` \| `organization`), `display_name`, `exact_key`, `merged_into?`, `revision` | identity is the id only; names are never keys (INV-CAT-007) |
| `agent_aliases` | `agent_id`, `alias`, `script` (`bengali` \| `latin`), `exact_key`, `loose_key` | `UNIQUE(exact_key, agent_id)`; feeds search ([search](search.md)) |
| `credits` | `version_id`, `agent_id?`, `raw_name?`, `role` (writer, translator, editor, compiler, illustrator, cover_artist, publisher), `ordinal` | PK `(version_id, role, ordinal)`; `agent_id` or `raw_name` present; `raw_name` becomes an agent on publish (exact-key dedupe); a contributor facet matches (role, agent) on one row |
| `series`, `version_series` | `series(id, name, exact_key)`; `version_series(version_id, series_id, ordinal numeric?)` | `UNIQUE(series_id, ordinal)` per published version when ordinal present |
| `categories`, `version_categories` | `categories(id, name, exact_key, parent_id?)`; join `(version_id, category_id)` | tree depth <= 3, acyclic |
| `field_overrides` | `book_id`, `field`, `value` (jsonb), `set_by`, `set_at`, `source_value_hash`, `stale` | PK `(book_id, field)`; exactly one effective source per field: the override wins; `stale` is set when a new version changes the source value (override still effective); `0` and `null` are distinct values (INV-CAT-006) |
| `metadata_revisions` | `id`, `book_id`, `version_id`, `revision_no`, `source` (`ingestion` \| `operator`), `changed_by`, `changed_at`, `changes` (jsonb field to [old, new]), `snapshot` (jsonb) | `UNIQUE(book_id, revision_no)`; append-only (REVOKE UPDATE, DELETE); restoring writes a new revision |
| `agent_merges` | `from_agent`, `into_agent`, `moved_credits` (jsonb), `at`, `by` | enables split and undo; `into` must be active so cycles are impossible |

## Tables: assets

| Table | Columns | Constraints |
|---|---|---|
| `assets` | `id`, `version_id`, `kind` (`epub` \| `cover` \| `preview`), `sha256`, `size_bytes`, `media_type`, `storage_path`, `created_at` | `UNIQUE(version_id, kind)`; write-once (trigger rejects UPDATE and DELETE except by the purge job); `epub` is `application/epub+zip` verified by magic bytes and ZIP structure; `cover` is a verified raster image within the size cap; `preview` is a `PreviewArtifact` re-sanitized on intake. INV-CAT-020, 021, 028 |

Layout, atomic write and sweep: [files](files.md).

## Tables: shelf, saved filters, Kindle, audit

| Table | Columns | Constraints |
|---|---|---|
| `shelf_entries` | `user_id`, `book_id`, `added_at` | PK `(user_id, book_id)`; add is idempotent; may point at a no-longer-visible book (hidden on read, never grants access). INV-CAT-025 |
| `saved_filters` | `id`, `user_id`, `name`, `query` (jsonb), `created_at` | `UNIQUE(user_id, name)` (duplicate gives typed 409 `duplicate_saved_filter`); count per user bounded by a configured limit (value not yet in [limits](../../04-architecture/cross-cutting/limits.md); needs a row); `query` validated against a schema on save and on apply; row visible only to `user_id`. INV-CAT-026, 033 |
| `kindle_requests` | `id`, `user_id`, `book_id`, `version_id`, `address_index`, `requested_at`, `status` (`queued` \| `sent` \| `failed`), `error_class?`, `reason?`, `idempotency_key` | `UNIQUE(user_id, idempotency_key)`; status updated by notify through `/internal/kindle-requests/{id}/status` (idempotent by request id and status). INV-CAT-029 |
| `download_log` | `id`, `user_id`, `book_id`, `version_id`, `at`, `kind` (`download` \| `kindle_internal` \| `reader_internal`) | INSERT-only; feeds rate limits |
| `audit_log` | `id`, `actor`, `action`, `target`, `at`, `details` | INSERT-only for the service role; written in the same transaction as the change; covers publish, unpublish, edit, merge, delete, file replace, export, EPUB download, Kindle request. INV-CAT-031 |

## Tables: search and events

| Table | Columns | Constraints |
|---|---|---|
| `search_docs` | `book_id` (PK), `version_id`, `doc` (tsvector), `title_sort`, `title_exact_key`, `facet_*` arrays, `language`, `published_at`, `normalizer_version` | row exists iff the book is publicly visible; written in the same transaction as the pointer; details in [search](search.md). INV-CAT-009, 012, 013 |
| `events` | `cursor` (bigserial), `id` (uuid7), `type`, `subject_id`, `payload`, `created_at` | written in the same transaction as the change; payload ids only; retained 30 days and not pruned past a known consumer cursor. INV-CAT-024 |
| `event_cursors` | `source` (PK), `last_cursor` | identity events; advanced in the same transaction as the effect |

## Invariants by id (where each is enforced)

| INV | Enforced by |
|---|---|
| INV-CAT-001 | `VersionState` type, transition table, TLA+ model |
| INV-CAT-002, 003 | one `visible_books` filter; reader-facing view types without source fields |
| INV-CAT-004 | trigger at `published`, unit test |
| INV-CAT-005 | immutable `id`, `UNIQUE(slug)`, `book_slugs` |
| INV-CAT-006 | revision check in the command, `field_overrides`, `metadata_revisions` |
| INV-CAT-007 | `agents` keyed by id, `agent_merges` |
| INV-CAT-008, 015, 016 | query builder, snapshot token, keyset |
| INV-CAT-009..014, 018 | [search](search.md) |
| INV-CAT-012, 019 | `PublicDocument`, `PreviewArtifact` types |
| INV-CAT-020..023, 028 | [files](files.md), [versions](versions.md) |
| INV-CAT-024 | outbox transaction rule |
| INV-CAT-025, 026, 033 | shelf and saved filter constraints above |
| INV-CAT-027, 029, 030, 031, 032 | [API](api-contract.md), audit table, GET handlers take a read-only connection |
