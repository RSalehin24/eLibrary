# ADR-0015 — Annotation anchors survive rebuilds

Status: REVIEW

## Context
EPUB CFI anchors break when chapters are regenerated.

## Decision
An `Anchor` = `{ section_id, quote: {prefix, exact, suffix}, position: {start, end} (UTF-16 offsets within section text), artifact_set_id, state }` following the W3C Web Annotation selector model. `section_id` is derived from the source key (UUIDv5 of book id + source path), not from ordinal order. Re-anchoring on a new artifact set: exact quote match in the same section → fuzzy match (bounded edit distance, prefix/suffix agreement) in the same section → search siblings → `Orphaned` (kept, shown, user-resolvable).

## Consequences
+ Highlights survive reprocessing; orphaning is explicit and measurable (gold: ≥ 99% re-anchor on non-semantic rebuilds).
− Needs a normalized text layer in the canonical document (it exists: block text).
