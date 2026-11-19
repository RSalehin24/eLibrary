# ADR-0015 — Annotation anchors survive rebuilds

Status: ACCEPTED

## Context
EPUB CFI anchors break when chapters are regenerated.

## Decision
An `Anchor` = `{ section_id, quote: {prefix, exact, suffix}, position: {start, end} (UTF-16 offsets within section text), book_version, state }` following the W3C Web Annotation selector model. `section_id` is derived from the EPUB source key (UUIDv5 of book id + spine item path), not from ordinal order. Re-anchoring when the reading copy of a new book version replaces the old one (`book.version_changed`; the anchor refers to the reading copy `(book_id, version)`, [ADR-0023](0023-reader-renders-whole-book.md)): exact quote match in the same section → fuzzy match (bounded edit distance, prefix/suffix agreement) in the same section → search siblings → `Orphaned` (kept, shown, user-resolvable). The reader service re-anchors on the server after the new copy is Ready (D-46); the browser does not re-anchor, and unmatched annotations are kept and flagged `orphaned`.

## Consequences
+ Highlights survive reprocessing; orphaning is explicit and measurable (gold: ≥ 99% re-anchor on non-semantic rebuilds).
− Needs a normalized text layer in the canonical document (it exists: block text).
