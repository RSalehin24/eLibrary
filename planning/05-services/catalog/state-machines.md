# catalog - state machines

Status: DRAFT

## Naming

The states are `published` and `archived` plus soft delete (REQ-CAT-001, INV-CAT-001). There is no `draft` (D-56: a version is born `published`), no `in_review` and no `rejected` state (D-49). Mapping of the planning brief words (no new states):

| Brief word | Stored as |
|---|---|
| candidate | not a catalog state: a build that has not passed every gate stays in ingestion's review queue and never reaches catalog |
| superseded | `archived` with `archived_reason = superseded` (a newer version was published) |
| unpublished | `archived` with `archived_reason = unpublished` (operator unpublish) |
| deleted | book-level tombstone (`books.deleted_at`), not a version state |

## Version publication (REQ-CAT-001, 021, 022; INV-CAT-001, 021, 022)

```
 ingestion publish (gates passed, one transaction) --> published --unpublish--> archived(unpublished)
                                                                  |        ^                       |
                                                                  |        +------restore----------+
                                                                  +--newer version published--> archived(superseded)
```

| Transition | Who | Guards | Effects (one transaction) |
|---|---|---|---|
| publish (intake) | service token (ingestion) | build identity `(book_id, build_hash)` unused, else return the existing version; artifacts verified (sha256, EPUB structure, cover bytes, preview re-sanitized); credit rule; slug free; book not deleted; size cap | insert version, assets, credits, `metadata_revisions` (source `ingestion`); state `published` (born published); set `current_version_id` and `latest_version_id`; previous published version to `archived(superseded)`; upsert `search_docs`; resolve `raw_name` credits; event `book.published`; when it supersedes an older version also `book.version_changed` (`replaced`) and no `book.unpublished` (the older version is archived silently; an ingestion request that built it stays as it is, nothing is rewritten); audit (actor: ingestion service) |
| unpublish | `manage_catalog` | version `published` | `archived(unpublished)`; `current_version_id = NULL`; delete `search_docs`; event `book.unpublished` (`archived`); audit |
| restore | `manage_catalog` | latest archived version, assets verified, book not deleted | `published`; pointer and search document restored; events `book.published`; audit |
| soft delete | `manage_catalog` (**OPEN O-4**) | any book | `books.deleted_at`; pointer kept so undelete restores; visibility predicate false; search document removed; shelf, files, Kindle stop resolving; event `book.unpublished` (`deleted`); blobs kept until the retention purge |
| undelete | `manage_catalog` | within retention | clear `deleted_at`; re-index if a published version exists; event `book.published` |

A publish call that fails a guard (hash mismatch, missing credit, slug taken, book deleted) returns a typed 4xx and commits nothing; ingestion records it as `catalog_rejected` (a failed-gate hold in its review queue, never a visible book). Illegal transitions return `409 invalid_transition`. Persistent state is the enum; in code the transitions consume a typed value, so a transition not in the table does not compile. The only paths to visibility are `publish` and `restore`. At most one published version per book (partial unique index). A failed build is never visible (REQ-CAT-001). Details of immutability and file retention: [versions](versions.md).

## Metadata edit (REQ-CAT-006)

`current revision r --PATCH If-Match r--> revision r+1 (history row appended)`; a stale `If-Match` is rejected, never merged. A published book keeps at least one qualifying credit or the command fails with `no_credit`. Field ownership: `source value -> operator override (effective) -> [new version changes source value] -> override flagged stale (still effective) -> operator keeps it or accepts the source`.

## Agent merge

`active -> merged(into)` with an `agent_merges` record; credits re-pointed in one transaction; split restores from the record; the target must be active.

## Asset write

`receiving (temp file) -> hashed -> fsync -> renamed into the blob store -> row inserted -> committed with the version`. A crash before commit leaves an orphan blob, swept after 24 h.

## Kindle request

`queued (row plus kindle.requested event, one transaction) -> sent | failed` (status reported by notify; notify's Queued and Retry report `queued`, Sent reports `sent`, Rejected, Preflight failure and Failed report `failed` with the reason, see [notify state machines](../notify/state-machines.md)). A limit breach returns 429 before any row is written. Idempotent on `(user_id, Idempotency-Key)`. Allowed only for a published version within the size cap.

## Event consumption (identity events)

`cursor n -> fetch page -> apply invalidation idempotently -> cursor n+k` in one transaction; a restart repeats at most one page.

## Search document

`absent -> present (publish, restore, undelete) -> absent (archive, delete)`; the `rebuild` command recomputes all rows from tables; rebuilt and incremental result sets must be equal (REQ-CAT-013).
