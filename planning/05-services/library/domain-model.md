# library — domain model

Status: DRAFT

| Entity | Fields | Notes |
|---|---|---|
| `ReadingSession` | `id`, `owner_id`, `book_id`, `device_class`, `artifact_set_id`, `state` (Preparing\|Active\|Closed), `opened_at`, `last_heartbeat_at` | unique partial index: one non-Closed per `(owner, book, device_class)` (INV-LIB-008) |
| `Progress` | `owner_id`, `book_id`, `section_id`, `offset`, `percent`, `revision`, `updated_at`, `artifact_set_id` | PK `(owner, book)`; update `WHERE revision < $new` |
| `Bookmark` | `id`, `owner_id`, `book_id`, `anchor`, `label?`, `created_at` | |
| `Highlight` | `id`, `owner_id`, `book_id`, `anchor`, `color`, `kind` (highlight\|underline), `note?`, `created_at`, `revision` | ≤ 5,000 per book |
| `Anchor` | `section_id`, `quote{prefix, exact, suffix}`, `position{start,end}`, `artifact_set_id`, `state` (Anchored\|Reanchored\|Orphaned), `confidence` | ADR-0015 |
| `ShelfEntry` | `owner_id`, `book_id`, `added_by` (created\|saved), `added_at` | PK `(owner, book)` (idempotent) |
| `SavedFilter` | `id`, `owner_id`, `target` (library\|catalog\|…), `query` (canonical JSON), `name` | round-trips (INV-LIB-006) |
| `book_ref` (projection) | `book_id`, `slug`, `title`, `state` | from catalog events |
| `section_index_projection` | `(artifact_set_id, section_id, text_hash, ordinal, title)` | from content |
| `kindle_sent_view` | `owner_id`, `book_id`, `sent_at` | from notify events |

## Re-anchoring algorithm (pure, `domain-anchor`)

Input: anchor + old section text + new section text (by `section_id`; if section missing, candidates from siblings by title/hash).
1. Exact `quote.exact` found once in new section → `Reanchored` at that position (check prefix/suffix agreement).
2. Found multiple → choose the occurrence maximizing prefix/suffix similarity; tie → `Orphaned`.
3. Not found → bounded fuzzy search (Levenshtein ratio ≥ 0.9 on `exact`, prefix/suffix agreement) within section → `Reanchored(confidence)`.
4. Else search sibling sections (same parent) → `Reanchored` with `moved=true`.
5. Else `Orphaned`. Never delete (INV-LIB-002).

Target: ≥ 99% `Anchored/Reanchored` on non-semantic rebuilds (whitespace, markup, title normalization) measured on a synthetic mutation set.
