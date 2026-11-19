# catalog - versions, immutability and publication

Status: DRAFT

How a gate-passing build becomes the visible book without a half-state (REQ-CAT-021, 022, 024; INV-CAT-021, 022, 024). State table: [state machines](state-machines.md).

## Rules

1. A `BookVersion` and its three assets (`epub`, `cover`, `preview`) are immutable once committed. Reprocessing creates version `n+1`; a published version is never edited. Metadata edits by an operator are separate commands recorded in `metadata_revisions` and in `field_overrides`; they change the effective metadata, not the stored EPUB.
2. Publish (intake) is one transaction: version row, assets rows, credits, history, switch of the current version, event; there is no approval step (D-49). The blobs are written and renamed before the transaction; a crash leaves only an orphan blob.
3. Idempotency: the build identity is `(book_id, build_hash)` where `build_hash` covers the curated document hash, the builder version and the artifacts. A replay returns the existing version with the same response. `source_hash` and `builder_version` are stored for provenance.
4. Publication is an atomic switch of `books.current_version_id` in the same transaction that archives the previous version, upserts `search_docs` and writes the events. A reader of the API sees the old or the new version, never a mix.
5. Retention: files of the previous published version are kept until the next version is published, then the previous one is `archived(superseded)` and its blobs become eligible for the purge job after a configured delay (value to be added to [limits](../../04-architecture/cross-cutting/limits.md)). Rows are never hard-deleted except by an audited retention job.
6. Reader coupling: `book.published` carries `version_id`; the reader fetches `GET /internal/books/{id}/versions/{version_id}/epub` for that exact version. `book.version_changed` (`replaced`) tells the reader a newer version supersedes the previous one; annotations are re-anchored by the reader ([reader anchors](../reader/anchors.md)). Catalog does not touch reading state.
7. Candidate size cap 50 MiB (Kindle mail limit); a larger body is `413`. Duplicate decisions are made by ingestion before it calls catalog; catalog answers `POST /internal/books/match` with exact and near matches but never merges.

## Version numbering

`version_no` is a per-book counter, assigned at intake, never reused. The book's `latest_version_id` points at the highest `version_no` in any state; `current_version_id` points at the published one.

## Source link and operator fields

The source URL lives in `book_sources` and on `/manage/*` only. A new version that changes a source-owned value does not overwrite an operator override (REQ-CAT-006); the override is marked `stale` and the operator decides.
