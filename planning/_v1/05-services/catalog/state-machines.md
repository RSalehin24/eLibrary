# catalog — state machines

Status: DRAFT

## Version publication (REQ-CAT-001, INV-CAT-001)

```
        submit (manual)          approve                 archive / replaced by newer approve
 draft ───────────────► in_review ───────► published ─────────────────────────────────► archived
   ▲  ◄──── reject ──────────┘                 ▲                                          │
   │                                           └──────────── restore ◄─────────────────────┘
   └ created by ingestion intake directly as in_review (draft only for manual creation)
```

| Transition | Who | Preconditions | Effects (one transaction) |
|---|---|---|---|
| intake (ingestion) | service token | idempotency key unused; EPUB/cover verified; preview sanitized | insert version `in_review`, assets, credits, open review, `metadata_revisions` (source `ingestion`); `books.latest_version_id` updated; no visibility change |
| submit | `manage_catalog` | version is `draft`, assets present | state `in_review`, open review |
| approve | `manage_catalog` | version `in_review`; `epub` asset hash re-verified; credit rule; slug free | state `published`; set `books.published_version_id`; previous published version to `archived`; upsert `search_docs`; resolve `raw_name` credits to agents; events `book.published` (+ `book.version_changed` if replaced); audit |
| reject | `manage_catalog` | version `in_review` | state `draft`, review `rejected` with reason; event `book.version_changed` (ingestion shows `CatalogRejected`) |
| archive | `manage_catalog` | version `published` | state `archived`; `published_version_id = NULL`; delete `search_docs`; event `book.unpublished` |
| restore | `manage_catalog` | latest archived version, assets verified, book not deleted | state `published`; pointer and search doc restored; event `book.published` |
| soft delete | `manage_catalog` | any | `books.deleted_at`; pointer kept (so undelete restores) but visibility predicate false; search doc removed; event `book.unpublished`; blobs kept until retention purge |
| undelete | `manage_catalog` | within retention | clear `deleted_at`; if version was published, re-index; event `book.published` |

Illegal transitions return `409 invalid_transition`. Persistent state is the enum; in code `Version<Draft>::submit`, `Version<InReview>::approve` consume the value (INV-CAT-001). Only the `published` version is visible; there is no path to visibility other than `approve` or `restore` (REQ-CAT-001). At most one published version per book (partial unique index).

## Metadata review

`open` → `approved` (with approve) | `rejected` (with reject); a new intake for the same book while a review is open supersedes the older `in_review` version (the older one goes to `draft` with reason `superseded`).

## Field override

`source value → admin override (active) → [new version changes source value] → override flagged stale (still effective) → admin keeps override or accepts source`. Concurrent edits: `If-Match` revision, 412 on mismatch (INV-CAT-004).

## Agent merge

`active → merged(into)` with an `agent_merges` record; credits re-pointed in one transaction; split restores from the record; merge requires `into` to be active, so cycles are impossible.

## Asset write

`receiving (temp file) → hashed → renamed into blob store → row inserted → (committed with the version)`. A crash before the commit leaves only an orphan blob, removed by the sweep after 24 h. Rows are immutable once committed (INV-CON-001 in its new form).

## Kindle request

`requested → issued (row + event) → [notify owns delivery]`; limit breach returns 429 before any row is written. Idempotent on `(user_id, Idempotency-Key)`.

## Event consumption (identity events)

`cursor n → fetch page → apply invalidation idempotently → cursor n+k`; restart repeats at most one page; duplicates are harmless.

## Search document

`absent → present (on approve/restore/undelete) → absent (on archive/delete)`; a rebuild command recomputes all rows from tables; rebuilt and incremental sets must be equal (INV-DSC-005).
