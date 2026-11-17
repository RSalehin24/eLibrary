# content — domain model

Status: DRAFT

| Entity | Fields | Constraints |
|---|---|---|
| `Blob` | `sha256` (PK), `size`, `media_type`, `created_at` | immutable; path derived from hash; verified on write and on read in repair mode |
| `CanonicalDocumentRecord` | `book_id`, `doc_hash` (blob), `schema_version`, `ruleset_version`, `conservation_report_hash` | unique `(book_id, doc_hash)` |
| `ArtifactSet` | `id`, `book_id`, `doc_hash`, `builder_version`, `state` (Building\|Sealed\|Retired), `epub_hash?`, `html_manifest_hash?`, `section_index_hash?`, `preview_hash?`, `cover_hash?`, `sealed_at?` | Sealed ⇒ all five hashes present; no UPDATE after Sealed except `state→Retired`; unique `(book_id, doc_hash, builder_version)` makes builds idempotent |
| `ActivePointer` | `book_id` (PK), `artifact_set_id`, `revision`, `activated_at` | FK to a Sealed set (checked in the same transaction) |
| `SectionIndexEntry` | within section index blob: `section_id`, `parent`, `ordinal`, `type`, `title`, `char_count`, `text_hash` | derived; used by library for anchors |
| `RetentionHold` | `artifact_set_id`, `reason` (ActiveOrPrevious\|AnnotationsPending\|Manual), `until` | deletion blocked while any hold exists |

## Value types

`Sha256`, `SectionId` (UUIDv5 over `book_id` + source key), `SafeHtml`, `PreviewArtifact`, `FullDocument`, `PublicDocument`, `Verified<Capability>`.

## Preview policy ([D-05](../../04-architecture/open-decisions.md))

`PreviewPolicy { include_cover, include_metadata, include_summary, include_toc, max_chars_first_chapter (default 3000, 0 allowed), per_book_override }`. The builder cuts at a paragraph boundary ≤ `max_chars`, never mid-grapheme; the result is stamped with the policy hash.

## Retention

Previous set held until `AnnotationReanchorDone` for that transition and ≥ 30 days; failed `Building` sets are deleted after 24 h; unreferenced blobs are garbage-collected by a mark-and-sweep that first lists, then deletes after a second confirming pass.
