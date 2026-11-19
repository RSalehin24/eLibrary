# reader - anchors and annotations across versions

Status: DRAFT; the policy for a new version is decided: server re-anchoring, option A (D-46).

Reconciles [ADR-0015](../../04-architecture/adr/0015-annotation-anchors.md) (anchors survive rebuilds) with [ADR-0023](../../04-architecture/adr/0023-reader-renders-whole-book.md) (reader renders whole book; the anchor refers to a reading copy `(book_id, version)`). ADR-0015 assumed a canonical document with a block text layer; that document is ingestion's and the reader never sees it. In this design the text layer is the one defined in [reading copy](reading-copy.md) and the anchor is relative to the sanitized section of a reading copy.

## Anchor (REQ-RDR-015; INV-RDR-015)

`{section_id, offset, quote?: {exact, prefix, suffix}}` plus `anchored_version` (the version whose copy the offsets refer to) and `anchor_state` (`placed` or `orphaned`).

- `section_id`: UUIDv5(book id, normalized spine item path), stable while the file name is stable.
- `offset`: UTF-16 code unit offset into the section text layer; the end offset is `offset + len(exact)` for highlights.
- `quote`: exact text with a bounded prefix and suffix (for example 32 characters each side), taken from the text layer; this is the selector that survives edits (W3C text quote selector).
- A bookmark may carry only `{section_id, offset}` plus a short quote; progress carries the same shape as a locator.
- Resolving an anchor returns a location or `orphaned`, never an error.

## Resolution algorithm (shared by all options; a pure function)

Input: anchor, target section text layer. Steps, stopping at the first success:

1. `offset` within bounds and text at `[offset, offset+len)` equals `exact`: placed (method `exact`).
2. `exact` occurs in the same section: choose the occurrence with the best prefix and suffix agreement, nearest to the old offset: placed (`exact`).
3. Fuzzy match within the same section: bounded edit distance relative to quote length, prefix or suffix agreement required: placed (`fuzzy`).
4. Search sibling sections (all sections for the same quote with agreement), to cover chapters that were split or merged: placed (`fuzzy`).
5. Otherwise `orphaned`: the annotation keeps its old quote and section label, stays visible in the notes page, is never deleted, and the user may re-place it manually.

Bounds: edit distance and candidate counts are capped so resolution is linear and cannot be used to exhaust CPU. Property tests and a mutation suite ([test plan](test-plan.md): TST-RDR-015, 016) target at least 99 percent placement on non-semantic rebuilds (ADR-0015 gold target) and zero deletions.

## What happens on a new published version (decided: option A, D-46)

Trigger: `book.version_changed` with change `replaced`, then the new copy becomes Ready.

The server re-anchors. A job runs the algorithm over every bookmark and highlight of the book (and the progress locator), writes the new `anchor`, `anchored_version` and `anchor_state`, and logs each outcome in `anchor_log` (`method`: `exact`, `fuzzy`, `section_only`, `none`). An annotation that cannot be matched is kept, flagged `orphaned` and stays visible; it is never deleted. Lists, the notes page and deep links therefore always carry a correct `anchor_state`. Lazy client re-anchoring (B) and pinning to the old version (C) were not chosen.

Progress on a new version (also D-46): a progress locator is resolved with the same algorithm; if it cannot be placed the reader opens at the start of the section if the section exists, else at the start of the book. Percent is recomputed from the new text layer.

## Invariants

- No version change deletes an annotation or bookmark (INV-RDR-004, 015).
- Re-anchoring is idempotent: running it twice on the same copy changes nothing (`resolve` on a placed anchor in its own version returns the same anchor).
- Orphaned annotations never block opening the book and never raise an error.
- The anchor never contains book text beyond the quote (bounded length, 5,000 characters maximum for `exact`).
