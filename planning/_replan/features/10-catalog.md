# Legacy catalog app - feature extraction (10-catalog)

Status: DRAFT (research evidence; read-only record)

Root: `archive/app/backend/apps/catalog` (paths below relative to it). Mounted under some API prefix (not in my files; urls.py is relative). All line refs are `file:line`.

## 1. Coverage

| file | lines | fully read |
|---|---|---|
| admin.py | 57 | yes |
| apps.py | 8 | yes |
| urls.py | 70 | yes |
| services.py | 241 | yes |
| models/__init__.py | 107 | yes |
| models/books.py | 334 | yes |
| models/catalog_codes.py | 260 | yes |
| models/choices.py | 63 | yes |
| models/entities.py | 112 | yes |
| models/utils.py | 20 | yes |
| views/__init__.py | 24 | yes |
| views/assets.py | 72 | yes |
| views/books.py | 110 | yes |
| views/details.py | 136 | yes |
| views/references.py | 163 | yes |
| views/shared.py | 359 | yes |
| serializers/__init__.py | 21 | yes |
| serializers/books.py | 309 | yes |
| serializers/common.py | 90 | yes |
| serializers/lists.py | 73 | yes |
| serializers/manual.py | 186 | yes |
| serializers/reviews.py | 29 | yes |
| exports/__init__.py | 15 | yes |
| exports/common.py | 121 | yes |
| exports/csv_exports.py | 50 | yes |
| exports/pdf_exports.py | 112 | yes |
| management/__init__.py, commands/__init__.py | 0/1 (blank) | yes |
| management/commands/audit_curated_catalog.py | 201 | yes |
| management/commands/repair_source_site_metadata.py | 546 | yes |
| __init__.py | 0 | yes (empty) |

Total 28 non-migration files (3891 lines) read in full. Migrations excluded by assignment. Outside-scope files only spot-checked by grep: `apps/common/permissions.py` (CanEditMetadata = scope METADATA_EDIT, allow_book_scoped=True; CanViewPhysicalBooksList = scope PHYSICAL_BOOKS_VIEW), and usages of BookGroup / UserBookKindleSend elsewhere.

## 2. HTTP endpoints (urls.py; 20 URL patterns, 21 method+path operations)

Common: all DRF; default auth classes from project settings (not in scope). "Auth" = `IsAuthenticated` unless stated. Slug segment is `<path:slug>` (so slugs may contain `/`; order of patterns matters, the catch-all `books/<path:slug>/` is last, urls.py:69).

| # | Method | Path | Permission | Params / body | Response | Side effects |
|---|---|---|---|---|---|---|
| 1 | GET | `books/` (urls.py:23, BookListView views/books.py:18) | IsAuthenticated | Book filters in section 3. Default record_type=digital. Paginates only if `page` or `limit` present; default limit 10, max 100 | Plain array of BookListSerializer, or `{entries, pagination{page,limit,total_count,page_count,has_previous,has_next}}` | none |
| 2 | GET | `books/export/` (views/books.py:45) | IsAuthenticated | `format` csv (default) or pdf (else 400 `{"detail":"format must be csv or pdf."}`), same filters as #1 (ignores paging; exports ALL matching, `list(queryset)`) | CSV attachment `catalog-books.csv` / `catalog-manual.csv` (UTF-8 with BOM) or PDF `catalog-*.pdf`; 503 if reportlab missing | none |
| 3 | GET | `books/tickets/` (views/books.py:63) | IsAuthenticated | same filters | PDF `catalog-tickets-books.pdf`/`-manual.pdf`; 503 if reportlab missing | none |
| 4 | GET | `categories/` (views/references.py:60) | IsAuthenticated | `q, author|writer, series, record_type, created_after/before, sort, page, limit` (default limit 60) | list or paginated, CategoryListSerializer | none |
| 5 | GET | `series/` (references.py:92) | IsAuthenticated | `q, author|writer, category, record_type, created_*, sort, page, limit` | same shape | none |
| 6 | GET | `writers/` (urls.py:28) | IsAuthenticated | `q, series, category, record_type, created_*, sort, page, limit`; role=author | same shape | none |
| 7 | GET | `translators/` | IsAuthenticated | same; role=translator | same | none |
| 8 | GET | `compilers/` | IsAuthenticated | same; role=compiler | same | none |
| 9 | GET | `editors/` | IsAuthenticated | same; roles=editor+compiler | same | none |
| 10 | GET | `publishers/` | IsAuthenticated | same; role=publisher (no prose-fragment exclusion) | same | none |
| 11 | GET | `manual-books/` (views/books.py:74) | CanViewPhysicalBooksList (scope PHYSICAL_BOOKS_VIEW) | same filters as #1; default record_type=manual; default limit 60 | list/paginated BookListSerializer | none |
| 12 | POST | `manual-books/` | same scope (list and create share one permission class) | body ManualBookCreateSerializer (section 4.8) | 201 BookDetailSerializer | creates Book (record_type=manual, state=ready, review_state=approved), contributors/series/categories, assigns catalog_code |
| 13 | PATCH/PUT (UpdateAPIView; both accepted, always partial=True because `kwargs.pop("partial", True)`) | `books/<slug>/metadata/` (urls.py:35, details.py:76) | CanEditMetadata (scope METADATA_EDIT, book-scoped allowed) | BookMetadataUpdateSerializer fields: title, summary, state, review_state, book_info_html, dedication_html, main_content_html, toc, contributors[{name,role}], series[], categories[], notes (write-only), price, binding, is_compilation, publisher, language | 200 BookDetailSerializer | writes two MetadataVersion rows (before/after), updates Book, replaces relations, recomputes catalog_code. Lookup uses `Book.objects` with NO deleted_at filter (soft-deleted books editable) |
| 14 | POST | `books/<slug>/assets/epub/` (views/assets.py:14) | CanEditMetadata | multipart `file` (.epub extension only) | 200 BookDetailSerializer | creates/overwrites GeneratedAsset(epub): deletes old file, saves new at `generated/<slug>/<title>.epub`, sets status ready, sha256, size, content_type, clears source_job/legacy_path |
| 15 | POST | `books/<slug>/regenerate/` (assets.py:41) | CanEditMetadata | none | 202 `{book, job{id,job_type,status,queue_name,retry_count,last_error,created_at,started_at,finished_at}, created}`; 400 `{detail}` on ValueError | calls `apps.ingestion.services.submissions.queue_reprocess_book(book, actor)` (queues processing job) |
| 16 | POST | `books/<slug>/my-books/` (books.py:94) | IsAuthenticated | none | 200 BookDetailSerializer (annotations set manually) | `UserBook.get_or_create(user, book)` (idempotent add to My Books) |
| 17 | DELETE | `books/<slug>/my-books/` | IsAuthenticated | none | 204 | deletes the user's UserBook row (no error if absent) |
| 18 | GET | `books/<slug>/metadata-versions/` (details.py:65) | IsAuthenticated + inline `user_has_scope(METADATA_EDIT, book)` else 403 | none | plain array `[{id,source,notes,created_at}]` newest first (snapshot NOT returned) | none; book lookup has no deleted filter, exact slug only |
| 19 | GET | `books/<slug>/metadata-reviews/` (details.py:93) | CanEditMetadata + inline book-scope check (403 text "...review metadata for this book.") | none | array of MetadataReviewSerializer (not paginated) | none |
| 20 | POST | `books/<slug>/metadata-reviews/` | same | `state` (ReviewState choice), `notes` | 201 MetadataReviewSerializer | saves review (requested_by=actor, reviewer=actor if state != "pending" else null); sets book.review_state=state; if state in {approved, rejected} sets book.metadata_last_reviewed_at=now |
| 21 | PATCH/PUT | `metadata-reviews/<uuid:pk>/` (details.py:117) | CanEditMetadata + inline scope check on review.book | `state`, `notes` (partial=True always) | 200 MetadataReviewSerializer | updates review; reviewer=actor (always, even when state unchanged); book.review_state=state; same metadata_last_reviewed_at rule |
| 22 | GET | `books/<slug>/` (details.py:19) | IsAuthenticated (no scope: any logged-in user can read any non-deleted book) | none | BookDetailSerializer | none |
| 23 | DELETE | `books/<slug>/` | IsAuthenticated + inline `user_has_scope(METADATA_EDIT, book)` else 403 "You do not have permission to delete this book." | none | 204 | soft delete: state=soft_deleted, deleted_at=now (save update_fields state, deleted_at, updated_at) |

(Counted: 23 method/path operations over 20 distinct URL patterns. #13 and #21 also accept PUT.)

Notes:
- No restore, hard-delete, list-deleted, duplicate-group, series/category CRUD, or Kindle-send endpoints in this app. Kindle-send is written in `apps/access/views/assets.py:275-276` (delete-then-create UserBookKindleSend); this app only reads it. Restore of soft-deleted books happens implicitly in ingestion (`find_deleted_book_by_title` used by ingestion persistence), see 4.2.
- Asset download URL name referenced: `access-book-asset-download` (lives in access app).
- Query parameter `format` on export collides with DRF's URL_FORMAT_OVERRIDE (default name `format`), so `?format=csv|pdf` also drives content negotiation via the passthrough renderers; any other value would 404 at negotiation before the view's own 400 (inference; settings not read).

## 3. Search / filter / sort in exact detail

All in `views/shared.py`. Base queryset (`BookQueryMixin.base_queryset`, shared.py:325) = `Book` filtered `deleted_at IS NULL`, NO filter on state/review_state (drafts, rejected, needs_review all visible to every authenticated user via list/detail), prefetches contributors/series/categories/generated_assets/source_urls, defers big text columns (summary, raw_*, html, toc, content_items), and annotates per requesting user: `is_in_my_books`, `user_owns_book` (Exists UserBook), `my_books_added_at` (UserBook.created_at), `has_sent_to_kindle`, `user_kindle_sent_at` (UserBookKindleSend.created_at), `latest_submission_at` (that user's latest BookSubmission.created_at for the book).

Normalization: `normalize_catalog_text` from `apps/common/text` (not in my scope; produces `normalized_*` columns stored at save time).

`normalized_text_search_clause(raw, normalized, raw_lookup, normalized_lookup)` (shared.py:31) = OR of:
1. `raw_lookup__icontains = raw_query` (raw text as typed, stripped)
2. if normalized_lookup and normalized_query: `normalized_lookup__contains = normalized_query` (case-sensitive contains on normalized column; normalized string assumed lowercase)
3. if the normalized query has >=2 whitespace tokens: `raw_lookup__iregex = tokens (re.escape'd) joined by [\s\-.–—(){}\[\],:;/'"_|]*` (zero-or-more separator characters between tokens, so "a b" matches "a-b", "a,b", "ab").

Book list `q` (shared.py:135): normalized = normalize_catalog_text(q). OR over:
- `catalog_code icontains q`
- title (raw `title`, `normalized_title`)
- contributor name (any role) (`book_contributors__contributor__name` / `normalized_name`)
- `book_contributors__contributor__catalog_code icontains q`
- series name (`book_series__series__name` / normalized)
- category name (`book_categories__category__name` / normalized)
- `book_categories__category__catalog_code icontains q`
- linked submissions: `linked_submissions__original_input icontains q` OR `linked_submissions__normalized_input contains normalized`; when `ownership=mine` additionally ANDed with `linked_submissions__submitter = request.user` (otherwise any user's submitted input text matches, which is an information leak of other users' submission inputs as search hits).
Not searched: summary, publisher (manual_publisher), edition, source URLs, slug.

Other filters (all AND, all use `.strip()`; empty ignored):
- `record_type`: `all` | digital | manual; invalid -> view default (books/ digital, manual-books/ manual) (shared.py:55).
- `ownership=mine`: `my_books_added_at IS NOT NULL`. `kindle_sent=mine`: `user_kindle_sent_at IS NOT NULL`. Other values ignored.
- Exact: `category_code` (category.catalog_code), `category_slug`, `state`, `review_state`, `submission_status` (linked_submissions__status), `processing_status` (processing_jobs__status). `book_code` = `catalog_code icontains`.
- Fuzzy (same clause as above): `series`, `category`.
- `author` (alias `writer`): requires some BookContributor role=author AND (separate `.filter()`, so potentially a different join row!) name match. Same for `translator` (role translator), `editor` (role in editor,compiler), `publisher` (role publisher AND name match in one Q). Note: successive `.filter()` calls on multi-valued relations create independent joins, so role and name can match different contributors of the same book (bug, section 7).
- `binding`: exact `manual_binding`.
- `writer_code`: role=author AND contributor.catalog_code == value (exact, uppercase NOT enforced), `writer_slug`: same with slug.
- `contributor` (+ `contributor_role`): fuzzy name match; role filter applied only if contributor_role valid (editor expands to editor+compiler); invalid/unset role -> any role.
- `contributor_code` / `contributor_slug` (+ `contributor_role`): exact; role filter in same `.filter()` call (correct single-join semantics).
- `created_after`, `created_before`: `parse_datetime or parse_date`; `created_at >= / <=`; invalid silently ignored; a date value for created_before compares against midnight (excludes that day's later times).
- `.distinct()` always applied after joins.
Sort (`sort` param, shared.py:303-319), whitelist: `catalog_code`, `title`, `created_at`, `manual_publisher` and `-` variants; with `ownership=mine` also `requested_at` -> `my_books_added_at`; with `kindle_sent=mine` also `sent_at` -> `user_kindle_sent_at`. Default sort `-created_at` (or `-requested_at` if ownership=mine). Invalid sort falls back to `-my_books_added_at` / `-user_kindle_sent_at` / `-created_at` in that precedence. Secondary key `-created_at` unless sorting by created_at. Title sort is raw DB collation (no Bengali collation handling); `-requested_at` is not valid unless ownership=mine (falls to default).
Pagination (`OptionalPaginationListMixin`, shared.py:83): only when `page` or `limit` in query. `bounded_positive_int` clamps limit to [1, max=100] (0 becomes 1, non-int -> default), page to [1, 10000], then clamped to page_count; count via a separate `queryset.count()`. Else legacy unpaginated full list (DRF default pagination, if configured, still applies via super().list - unknown).

Reference lists (categories/series/writers/...; references.py):
- `annotate_reference_counts` adds `digital_book_count`, `manual_book_count`, `book_count` (Count distinct of books through relation, excluding deleted books; `book_count` depends on `record_type`: manual/all/else digital; default digital).
- Entity `q`: same fuzzy clause on `name`/`normalized_name` OR `catalog_code icontains`.
- Only entities with `book_count > 0` are returned.
- Exact-match (not fuzzy) filters: `author|writer` (category and series lists only; matches book's author contributor name), `series` (categories and contributor lists), `category` (series and contributor lists).
- Sort whitelist: catalog_code, name, created_at, book_count and `-`; default `-book_count`; secondary `name`.
- Contributor lists: roles per page (writers=author; translators=translator; compilers=compiler; editors=editor+compiler; publishers=publisher). Except publishers, entities whose `normalized_name` matches `PROSE_FRAGMENT_PATTERN` (regex `(^| )(word1|word2...)($| )` over `ENGLISH_PROSE_FRAGMENT_WORDS` imported from ingestion) are excluded (noise heuristic against scraper garbage). Unknown `role` kwarg falls back to author.
- Serializer name uses `clean_entity_display_text(name)` at read time.

## 4. Domain mechanics

### 4.1 Catalog codes (models/catalog_codes.py)
- 10-character code over alphabet `23456789ABCDEFGHJKLMNPQRSTUVWXYZ` (32 symbols, no 0/1/I/O), i.e. 50 bits. Unique, nullable, indexed, uppercased on save.
- Not random/not a counter: payload bits are put through an affine "scramble" `(payload*M + offset) mod 32^10` with odd multipliers (entity M=741103597443, book M=853731903539) and per-type offsets; decode via modular inverse. Pure obfuscation; constants are in source. Decode validates tag/salt/check.
- Entity code (Contributor "writer", Series, Category): payload = tag(2 bits: series 0, category 1, writer 2) | sequence(16 bits) | salt(32 bits = f(sequence,tag), multiplicative-hash XOR). Sequence = max decoded sequence of all existing valid codes in that table + 1 (full table scan each save), starting at 1; capacity 65535 then ValueError. Offsets differ per entity type so a code is only valid for its own type.
- Book code: payload = tag 3 (2 bits) | category sequence (16) | writer sequence (16) | per-pair book sequence (12 bits) | check (4 bits = XOR/multiply hash & 15). Book sequence = max over ALL other books (incl. soft-deleted) with same (category_seq, writer_seq) + 1, capacity 4095 per pair; ValueError beyond. Category seq = first category (by category name ASC) with a valid code; writer seq = first contributor with role=author ordered by sort_order, name. Unknown relation = 0.
- Consequence: a book's code encodes its primary category and primary author; the code is recomputed whenever those change (`build_book_catalog_code` keeps the current code only if its embedded seqs equal the current ones), so codes are NOT stable identifiers after metadata edits. `derive_category/writer_catalog_code_from_book_code` allow deriving entity codes from a book code (used for lookups elsewhere).
- Book.save (books.py:95): clean title, normalize, refresh slug if needed, upper-case code or None, `super().save()`, then if code missing/invalid, compute and `UPDATE` it separately (two writes; first insert has NULL code). `sync_book_catalog_code` (services.py:161) re-runs after relation replacement.
- Concurrency: sequence assignment is read-max-then-write without locking/transaction; unique constraint is the only guard (race -> IntegrityError).

### 4.2 Slugs, soft delete, restore, duplicates
- Slug: `SlugField(unique, allow_unicode)`, built from `unicode_slugify(value) or "item"` with `-2, -3...` suffix on collision (utils.py:4). Regenerated whenever title (Book) / name (entities) differs from the stored value (`_should_refresh_slug`), so renaming changes URLs; old slugs are not kept as redirects. `BookDetailView.get_object` has a fallback: if exact slug not found, scans all non-deleted books (iterating `id,title,slug`) and compares `slugify(title, allow_unicode=True) == slug` (details.py:41-53), O(n) scan on 404 path. Entities use the same builder (slug on Contributor/Series/Category).
- Soft delete: `SoftDeleteModel` (apps.common; `deleted_at` field) + `LifecycleState.SOFT_DELETED`. Only trigger in this app: DELETE `books/<slug>/` (needs METADATA_EDIT, possibly book-scoped) and the repair command `soft_delete_duplicate_failed_books`. All list/detail querysets filter `deleted_at IS NULL`.
- Restore: none in catalog views. `find_deleted_book_by_title(title)` (services.py:135) returns the most recently deleted book with same `source_site` (= `get_source_site_domain()`) and `normalized_title`; ingestion persistence reuses it ("existing_book = target_book or find_deleted_book_by_title") i.e. re-submission of a deleted title resurrects/reuses the deleted row (logic in ingestion, outside scope). `find_existing_book_by_title` (same site + normalized_title, not deleted, newest) and `find_existing_book_by_source_url` (BookSource.normalized_source_url) are the dedupe lookups for ingestion.
- Duplicate/edition grouping: `BookGroup(canonical_title, normalized_canonical_title, note)` and `Book.group` (FK SET_NULL), `Book.edition`/`normalized_edition`. No catalog endpoint exposes groups or edition (serializers omit them). Created/used by ingestion duplicate detection (`ingestion/.../detection.py` suggested_group; `processing/service_modules/request_action_dispatch.py` creates a BookGroup lazily and wires both books; `curated_persistence.py` honours a group hint). `Book.Meta.constraints = []`: no DB uniqueness on title/edition/source_site.
- Source tracking: `Book.source_site` (string, default ""; manual books get `manual-library:<uuid4 hex>`), `BookSource` (one per book via `unique_together=("book",)` yet the code and serializers treat `source_urls` as a list and `is_primary` flag; `normalized_source_url` globally unique).

### 4.3 Contributor roles
`ContributorRole`: author, translator, compiler, editor, illustrator, cover_artist, publisher, other. `BookContributor(book, contributor, role, raw_value, sort_order)` unique (book, contributor, role); ordering by sort_order then name. `Contributor` unique by both `name` and `normalized_name`. "Editor" filters/pages always include "compiler" (editors page, editor filter, CSV "Editors" column, export "Editor:" line). Manual create folds compilers into role EDITOR (compiler role lost, serializers/manual.py:84). List serializer only emits authors/translators/compilers/editors (illustrator/cover_artist/publisher/other appear only in `contributors` of detail, publisher is also `publisher` field = `manual_publisher`).
`normalize_book_contributors` (services.py:29): clean names, dedupe on (normalized name, role), empty dropped, missing role -> author, and any AUTHOR entry whose normalized name also occurs under a non-author role is dropped (a person who is translator is not also shown as author). Applied on read (list: cached on object as `_normalized_contributors`) and on write.
Read-time noise filter: `looks_like_contributor_name(name, role)` (ingestion normalization) drops garbage contributor rows from list output. Detail additionally parses contributors out of front-matter HTML (`extract_front_matter_entries(combined_front_matter_html(book_info_html, main_content_html))`, `split_contributor_value`) and merges them into `contributors`/`authors`; non-role front-matter entries returned as `front_matter[{key,label,value,role}]`.

### 4.4 Series and categories
`Series`, `Category`: name unique + normalized_name unique + slug unique + catalog_code. M2M through `BookSeries(sort_order, raw_value)` unique(book, series) and `BookCategory(raw_value)` unique(book, category). Created on demand by name via `get_or_create_*` keyed on `normalized_name`; display name updated for contributors only (series/category keep first-seen casing). Flat lists: no hierarchy, no parent category. Manual create requires >=1 category; series optional.

### 4.5 Manual (physical) books
`record_type` digital|manual; manual-only fields on Book: `manual_is_compilation`, `manual_binding` (hard_cover|paper_back), `manual_publisher` (free text), `manual_price` Decimal(10,2), `manual_language` ("bn" default | "en"). Exposed in list serializer as publisher/price/is_compilation/language/binding(display label). Create (`ManualBookCreateSerializer`, manual.py:12): required `title`, `writers` (may be empty list but see rule), `categories` (>=1 after normalization); optional summary, translators, compilers, editors, series, is_compilation, binding, publisher, price, language. Rule: at least one of writers/translators/compilers/editors. Names cleaned via `normalize_name_list` (clean_entity_display_text, dedupe by normalized key, order preserved). Creates Book(state=ready, review_state=approved, source_site=`manual-library:<uuid>`, raw_scraped_metadata/raw_scrape_payload={"manual_entry":True}); publisher also stored as a Contributor with role publisher. No duplicate check for manual books (same title+writer creates another row, with a new catalog code sequence).

### 4.6 Metadata review and versioning
- `Book.review_state` (ReviewState: pending default, approved, rejected, needs_review...; enum in apps.common) and `Book.state` (LifecycleState: draft default, ready, needs_review, archived, soft_deleted ...). `Book.metadata_last_reviewed_at`.
- `MetadataReview(book, state, requested_by, reviewer, notes)`; creating a review overwrites the book's review_state. History is the list of reviews.
- `MetadataVersion(book, snapshot JSON, source, notes, created_by)`: on every metadata PATCH two snapshots (`manual_edit_before`, `manual_edit_after`) with title, summary, state, review_state, book_info_html, dedication_html, main_content_html, toc, contributors[{name,role}], series[], categories[], price (str or None; 0 becomes None), binding, is_compilation, publisher, language. Default source "scrape" for others (writers elsewhere). No endpoint to view a snapshot or revert (list returns metadata only).
- Metadata update validation: `contributors` if provided must contain at least one entry with role in author/translator/editor/compiler and a name (so a payload with only publisher fails; also an empty list fails). `state`/`review_state` are writable directly through the generic update with no transition rules and no review record created.
- Update flow: snapshot -> setattr all validated fields -> `instance.save()` (rewrites slug if title changed) -> `replace_book_relations` (delete-all then recreate; only for provided keys; recomputes catalog code) -> snapshot. Not wrapped in a transaction.

### 4.7 Ownership (UserBook) and Kindle
- `UserBook(user, book)` unique; POST/DELETE `books/<slug>/my-books/`; surfaces as `is_in_my_books`, `my_books_added_at`; list filter `ownership=mine`, sort `requested_at`. The same annotation `user_owns_book` exists but is not serialized (dead).
- `UserBookKindleSend(user, book)` unique pair; written by access app (replaces any existing row so `created_at` = last send). Exposed `has_sent_to_kindle`, `user_kindle_sent_at`; filter `kindle_sent=mine`, sort `sent_at`. Not registered in admin.
- `latest_submission_at`: the requesting user's most recent submission linked to the book.

### 4.8 Serializer output (what the UI contract is)
List item: id, catalog_code, record_type, title, slug, state, review_state, authors[], translators[], compilers[], editors[], contributors[{name,role,...}], series[names], categories[names], binding (label), publisher, price, is_compilation, language, cover_download_url (empty unless user may view cover and a READY cover asset exists on disk/legacy_path), latest_submission_at, is_in_my_books, my_books_added_at, primary_source{url,display_url,display_path,source_title,source_type,site,is_primary} (primary or first; visible to everyone, unlike detail's `source_urls`), created_at, has_epub_asset (one query per row, N+1), has_sent_to_kindle, user_kindle_sent_at.
Detail adds: assets[{id,asset_type,status,content_type,file_size,download_url}] (download_url gated per type: cover -> view cover, html -> view preview html, epub -> download assets permission; empty if file missing), source_urls and source_records (only with VIEW_SOURCE_RECORDS scope), front_matter, latest_processing_job (first of prefetched processing_jobs), book_info_html (merged), dedication_html (cleaned), toc, empty_chapters (recursive list of non-"section" toc nodes without has_content True), empty_chapters_count, metadata_last_reviewed_at, raw_provenance (raw_scraped_metadata + raw_scrape_payload only if `is_staff`), can_launch_reader, can_view_preview_html (permission helper functions in common.permissions).

### 4.9 Assets
- `GeneratedAsset(book, asset_type html|epub|cover, status pending|ready|failed, file, storage_path, legacy_path, content_type, file_size, checksum, is_protected default True, source_job)`; unique (book, asset_type) so one asset per type. Upload path `generated/<book.slug>/<filename>`. `asset_exists` checks storage.exists, then local path, then `legacy_path` on disk (legacy migration artifacts). Download endpoint is in the access app. EPUB replace: extension check only (no zip/mimetype validation, no size limit, whole file read into memory); sets checksum sha256. Filename is `"{book.title}.epub"` (title may contain unsafe characters; Django storage sanitizes).
- `Book.cover_source_url`, `main_content_html`, `book_info_html`, `dedication_html`, `toc` (nested JSON: nodes with type, title, has_content, source_url, path, children), `content_items`, `empty_chapters_count` hold scraped book content.

### 4.10 Curated-document models (no HTTP surface here)
`CuratedBookDocument` (source_url, version, status draft|validated|review_required|invalid, structure_type, validation_summary, source_snapshot, document JSON, unique(source_url, version), book SET_NULL), `CuratedEntity` (entity_type work|person|organization|series|category|asset|publication_event|metadata, role, value, normalized_value, evidence...), `CuratedSection` (section_id unique per doc; types cover/title_page/book_info/dedication/front_matter/generated_toc/body/back_matter; html; sort_order), `CuratedEvidence`. Written by ingestion curated pipeline; only read here by the audit command and Django admin.

### 4.11 Exports
- CSV (`exports/csv_exports.py`): BOM + header: Book ID (= catalog_code), Title, "Writer / Translator / Editor / Publisher" (lines joined " | "), Writers, Translators, Editors (editor+compiler), Publishers, Categories, Series, Type (Manual/Digital), Compilation (Yes/No), Binding, Publisher, Price, Created At (ISO). Contributor names via `normalize_book_contributors` (author-dedupe rule applies). Values are NOT neutralized for CSV/formula injection (title starting with `=`).
- Book list PDF (reportlab; landscape A4; columns Book ID/Title/Writer/Category/Details/Price/Created; manual details = Publisher, Binding, Compilation; digital details = series or "Standalone" + "Digital"; categories empty -> "Unsorted"; header colour #0b3d2e). Title "Manual Book List"/"Book List". Fonts: `settings.CATALOG_EXPORT_FONT_PATH` then hard-coded Noto Sans Bengali / Noto Sans / DejaVu / macOS font paths, else Helvetica (which cannot render Bengali). reportlab is an optional import; missing -> RuntimeError -> HTTP 503.
- Tickets PDF: portrait A4, 3-column grid of cells (bold catalog code, title, contributor line `authors | Translator: .. | Editor: .. | Publisher: ..`, "Contributor unavailable" fallback), 64 mm columns, no page header per cell, no barcode/QR.
- Filenames `catalog-{books|manual}.{csv|pdf}`, `catalog-tickets-{books|manual}.pdf`; `record_type=all` yields the "books" suffix.
- Export filters = book list filters (all; includes ownership/kindle). No row cap, evaluated fully in memory (N queries for contributors per book mitigated by prefetch).

## 5. services.py business rules (241 lines)
- `canonical_display_name` = `clean_entity_display_text`; `canonical_contributor_role(role)`: falsy -> author.
- `normalize_book_contributors`: see 4.3.
- `get_or_create_contributor/series/category(name)`: clean, normalize, empty -> None; `get_or_create(normalized_name=..., defaults={name})`. Contributor: if stored name != cleaned name, rename (updates slug/code via save); ensure valid writer catalog code else save() again. Category: ensure valid category code. Series: no code repair step (relies on save()).
- `normalized_book_title`, `find_existing_book_by_title`, `find_deleted_book_by_title`, `find_existing_book_by_source_url`: ingestion dedupe (see 4.2). They filter on `source_site == get_source_site_domain()` (from `ingestion.services.resolution_support_hosts`), so dedupe is scoped to one configured site.
- `sync_book_catalog_code(book)`: unsaved -> save; else recompute and write if changed.
- `replace_book_relations(book, contributors=None, series_names=None, category_names=None)`: None = leave untouched; otherwise delete all existing links and recreate with dedupe (by normalized name/key), `sort_order` = index in input (contributors/series; index counts skipped items too), `raw_value` default name; ends with `sync_book_catalog_code`. This is the single write path for relations used by manual create, metadata update, and the repair command (and presumably ingestion).

## 6. Management commands
1. `audit_curated_catalog` (read-only): args `--report-path` (default `/app/logs/audit_curated_catalog.json`), `--failure-sample-size` 50, `--media-root` (default `/storage/media/scraped-books`; accepted but UNUSED). Counts books (including deleted), curated docs, contributors, book-contributors; quarantined = review_state rejected AND state archived; needs_review count; structure_type histogram; contributor-role counts; EPUB health per EPUB asset (file missing, <1 KiB, bad zip, no non-empty content XHTML besides nav/cover, missing nav.xhtml) with samples; `books_without_epub_asset`. Writes JSON file, prints totals and epub_health.
2. `repair_source_site_metadata`: args `--dry-run`, `--retry-failed-epubs`, `--repair-epub-nav`, `--regenerate-corrupt-epubs`, `--limit N`. Always runs, in order: (a) `update_source_entries` re-parse SourceCatalogEntry title/author line via `split_display_title`; (b) `update_books` re-normalize every Book with non-null raw_scrape_payload (title overwritten from source catalog entry or payload, raw metadata rebuilt, relations replaced, BookSource.source_title updated) - NOTE `filter(raw_scrape_payload__isnull=False)` matches all JSON-default rows, and skipped only if payload empty; (c) clean contributor display names; (d) update processing BookRecord rows (name/writer/translator/publisher/category); (e) delete BookContributor rows failing `looks_like_contributor_name(role)` (not limited by `--limit`); (f) delete orphan noise Contributors (no contributions and no permission_grants); optional (g) repair EPUB spine so nav `itemref` is last with `linear="no"` and update size/checksum; (h) regenerate corrupt EPUBs (unreadable content.opf) from `raw_scrape_payload` via `epub_book.create_epub`; (i) soft-delete NEEDS_REVIEW books without sources whose title matches a sourced book; (j) re-queue FAILED BookCreationRequests with "Missing generated assets: EPUB". Prints a summary dict. In dry-run (b) counts but (d) etc compute properly; (j) and (i) respect dry-run. Not transactional; manual GC every N rows (memory pressure from big payloads).

## 7. Bugs, dead code, duplication, surprises
1. Catalog book codes change when primary category or primary author changes (embedded sequences), contradicting a "stable ID" expectation; sequence = max+1 table scan per save, racy; 4-bit check is weak; 16-bit entity and 12-bit per-pair capacities cause ValueError (500) at 65535 / 4095. Rebuild should use a stable ID separate from any structured code.
2. Any authenticated user can list/read ANY non-deleted book regardless of `state`/`review_state` (draft, rejected, needs_review) and see `primary_source` (source URL) in list output; `source_urls` gating only applies to detail. `ownership=mine` search of submission text; non-mine search matches other users' submission `original_input` strings.
3. Role+name filters (`author`, `translator`, `editor`) use two chained `.filter()` calls on multi-valued joins, so role and name can match different contributor rows (wrong results). `publisher` filter uses a single Q (correct); `contributor_code/slug` correct. Writer filter `writer_code` unnormalized (case-sensitive exact) while the q search uses icontains.
4. `BookMetadataUpdateView`, `MetadataVersionListView`, `MetadataReview*` use `Book.objects` / get_object_or_404 without `deleted_at` filter (soft-deleted books still editable/reviewable), whereas detail/assets filter it. Metadata-update PUT is silently partial.
5. Metadata update lets callers set `state`/`review_state` directly (e.g. mark approved without a review record); no transition validation; no optimistic locking; two MetadataVersion rows per edit even if nothing changed; snapshot `price` of 0 becomes None; snapshot cannot be restored.
6. `validate_contributors` requires author/translator/editor/compiler - publisher-only or empty contributors list rejected; also `replace_book_relations` deletes the existing publisher contributor if the client doesn't resend it (manual create stores publisher as a contributor AND `manual_publisher`; update of `publisher` field does not sync the contributor row -> two sources of truth).
7. Manual create folds `compilers` into role EDITOR (compiler distinction lost) though compilers can exist from scrapes; `validate_*` use assigned lambdas (style) ; `language` ChoiceField with `allow_blank` + default.
8. `BookSource` has `unique_together=("book",)` (one source per book) yet is modelled/serialized as a list with `is_primary`; `normalized_source_url` globally unique.
9. `BookMyBooksView` POST sets annotations on a non-annotated Book instance manually; `user_owns_book` annotation unused; `BookMyBooksView` has no state check.
10. `BookDetailView.get_object` slug fallback scans all books (O(n)) and uses Django `slugify` vs `unicode_slugify` in the model (possible mismatch). Slug changes on every rename without redirects; `<path:slug>` catch-all allows slashes and shadows later routes (ordering dependence).
11. N+1 / perf: `get_has_epub_asset` queries per row despite prefetch; `looks_like_contributor_name` regex work per row; catalog code generation loads every code; `list(self.get_queryset())` for exports (unbounded); `.distinct()` + heavy OR joins on q (6 joins) is slow at scale; `queryset.count()` with joins.
12. Dead/unused: `export_record_type` (identity wrapper around requested_record_type), `user_owns_book`, `--media-root` option, unused imports (`BytesIO`, `StringIO` in exports/common.py, `Subquery` ok, `CATALOG_CODE_LENGTH` etc.), `__import__("csv")`/`__import__("html")` inline hacks, duplicated sort_field dict copy-pasted 3x in references.py, `filter_map` dict-of-dicts hack with None placeholder, `"contributor": {}` loop hack, `apps/catalog/views/__init__.py` re-exports `queue_reprocess_book` so assets.py can import it via `catalog_views.queue_reprocess_book` (test-patching indirection), duplicate `ContributorListSerializer` in serializers `__all__`, `admin.py` does not register BookGroup/UserBookKindleSend/Contributor-related others, `BookGroup.note` and `Book.edition` never exposed by API, `Book.cover_source_url` not exposed, `GeneratedAsset.is_protected` unused here, `CuratedEvidence.__str__` missing, `MetadataReview/Version` no `__str__`.
13. Pagination contract is two-shape (array vs `{entries, pagination}`) depending on presence of `page`/`limit`; BookListView default limit 10 vs 60 elsewhere; page clamped to last page rather than 404.
14. Export: CSV injection not escaped; Bengali PDFs depend on host font files (silent fallback to Helvetica renders tofu); ticket PDF no page numbering; export `format` param name overlaps DRF format override.
15. `metadata_last_reviewed_at` only updated for approved/rejected; `needs_review`/other states leave it; review `reviewer` set on every update call even for notes-only changes; two views duplicate the same state-transition code.
16. `Book.save` does a second UPDATE for catalog_code; soft-deleted books still count in per-pair sequences and in `books_without_epub_asset`/totals in the audit.
17. `CanViewPhysicalBooksList` guards both list and create of manual books (no separate create/edit permission); no update/delete endpoint specific to manual books beyond the generic metadata and delete endpoints (delete needs METADATA_EDIT).
18. `repair_source_site_metadata` mutates Book titles from external catalog data on every run, and `delete_invalid_*` steps ignore `--limit` and run destructive deletes by default (only `--dry-run` prevents). Rows named in the docstring reference Bengali noise examples.
19. `get_or_create_contributor` race: concurrent creates hit unique `normalized_name` (IntegrityError, not retried).
20. Entity name uniqueness: `name` unique AND `normalized_name` unique; renaming to a name whose normalized form collides with another entity raises IntegrityError at save (no merge function; no merge/rename/delete endpoints for authors/series/categories at all -> data fixes only via admin/commands).

## 8. Unread files and why
None unread within the assignment (migrations excluded by instruction). Outside scope and only grepped, not read: `apps/common/{models,text,permissions,url_utils}.py`, `apps/ingestion/*`, `apps/processing/*`, `apps/access/*` (their behaviour is inferred only from names/imports and a few grep hits above).
