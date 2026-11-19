# Block IR

Status: DRAFT (reconciled with the single-pipeline design; kept from v1; requirements REQ-ING-013, 014; invariant INV-ING-014)

The intermediate representation that makes conservation checkable. It is an in-memory/pure-stage type; the persisted result is the curated document ([domain model](../domain-model.md), `curated_documents`), not a separate content-addressed store.

## Definition

```rust
pub struct Block {
    pub id: BlockId,             // hash(page sha256, dom_path, ordinal): stable across reruns
    pub kind: BlockKind,         // Heading{level 1..6} | Paragraph | ListItem{depth} | Quote | Image | Separator | TableRow | Verse
    pub text: DisplayText,       // NFC, whitespace-collapsed plain text
    pub html: SafeHtml,          // sanitized inline markup (strong, em, a, br, sup, sub, ruby)
    pub marks: Marks,            // strong_only, has_break, has_link, all_caps, ends_with_danda, ...
    pub origin: Origin,          // page url_key, page sha256, dom path, ordinal in page
}
pub struct Page { pub origin: PageRef, pub blocks: Vec<Block>, pub chrome: Vec<ChromeBlock> }
```

## Parsing rules (HTML to blocks)

1. Parse with a spec-compliant HTML5 parser; never regex HTML. (Any parser crate needs owner approval and a row in the dependency policy.)
2. Select the main content container via the adapter (`entry-content` equivalent); everything else is `chrome`.
3. Tag allow-list for blocks: `h1-h6, p, li, blockquote, pre, figure/img, hr, tr`. Other containers are unwrapped; children are processed in document order.
4. `<br>` inside a block keeps it as one block with `has_break`; the classifier may split it and records the split (ids derive from `(block id, line index)`).
5. `<p><strong>...</strong></p>` with no other text is marked `strong_only` (heading candidate).
6. `hr`, centered dots (`.`, `।`, `...`, `* * *`) become `Separator`.
7. Images keep resolved `src`, `alt`, dimensions; blocked if the scheme is not http/https/data-image. The image file is fetched by acquisition (GET only, same host allow-list) and referenced by its scrape-cache hash.
8. Inline `a` keeps `href` only when http(s) or an internal anchor; `javascript:` is dropped.
9. Whitespace: collapse runs; keep NBSP only as a mark; preserve ZWJ/ZWNJ in display text (they are removed only in matching keys).

## Chrome

Navigation, login prompts, "Bookmark", sharing, footer and empty containers are recognized by the adapter's chrome selectors and a ruleset phrase list. They are not discarded silently: they become `ChromeBlock{reason, origin}` and count in the ledger as `Dropped(SourceChrome)`.

## Conservation ledger

```
Ledger { input: Multiset<BlockId>, placed: Map<BlockId, Location>, dropped: Map<BlockId, ReasonCode> }
assert input == placed.keys + dropped.keys          // checked after every stage that consumes blocks
```

`ReasonCode` is a closed enum: `SourceChrome, DuplicateOf(BlockId), InlineTocSuperseded, TitleAuthorEcho, EmptyAfterNormalization, SeparatorOnly, PromotedCopy`. A new reason needs a reviewed plan change. A violation is a `ConservationFailure` review item and an `invariant_violation` metric, never a silent pass.

## Text layer

The concatenated `text` of a section's blocks (with `\n` between blocks) is the normalized text layer stored in the curated document with a hash. It is used for diffs and for the reader's optional in-book search; the reader re-derives its own anchors from the EPUB (anchors are a reader concern, not an ingestion output).
