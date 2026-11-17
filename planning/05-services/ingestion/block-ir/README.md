# Block IR

Status: DRAFT

The intermediate representation that makes conservation checkable.

## Definition

```rust
pub struct Block {
    pub id: BlockId,             // hash(snapshot_page_hash, dom_path, ordinal): stable across reruns
    pub kind: BlockKind,         // Heading{level 1..6} | Paragraph | ListItem{depth} | Quote | Image | Separator | TableRow | Verse
    pub text: DisplayText,       // NFC, whitespace-collapsed plain text
    pub html: SafeHtml,          // sanitized inline markup (strong, em, a, br, sup, sub, ruby)
    pub marks: Marks,            // strong_only, has_break, has_link, all_caps, ends_with_danda, …
    pub origin: Origin,          // page url, page hash, dom path, ordinal in page
}
pub struct Page { pub origin: PageRef, pub blocks: Vec<Block>, pub chrome: Vec<ChromeBlock> }
```

## Parsing rules (HTML → blocks)

1. Parse with a spec-compliant HTML5 parser (`html5ever`); never regex HTML.
2. Select the main content container via the adapter (`entry-content` equivalent); everything else is `chrome`.
3. Tag allow-list for blocks: `h1–h6, p, li, blockquote, pre, figure/img, hr, tr`. Other containers are unwrapped; their children are processed in document order.
4. `<br>` inside a block splits it into **lines** kept as one block with `has_break`; the classifier may split into sub-blocks and records the split (ids derive from `(block id, line index)`).
5. `<p><strong>…</strong></p>` with no other text is marked `strong_only` (treated as a heading candidate — spec §5).
6. `hr`, centered dots (`.`, `।`, `...`, `* * *`) and similar become `Separator`.
7. Images keep `src` (resolved), `alt`, dimensions; blocked if scheme not http/https/data-image.
8. Inline `a` keeps `href` only when http(s) or an internal anchor; `javascript:` is dropped.
9. Whitespace: collapse runs; keep NBSP only as a mark; preserve ZWJ/ZWNJ in display text.

## Chrome

Navigation, login prompts, "Bookmark", sharing, footer, empty containers and similar are recognized by the adapter's chrome selectors and by a ruleset list of chrome phrases. They are **not discarded silently**: they become `ChromeBlock{reason, origin}` and count in the conservation ledger as `Dropped(SourceChrome)`.

## Conservation ledger

```
Ledger { input: Multiset<BlockId>, placed: Map<BlockId, Location>, dropped: Map<BlockId, ReasonCode> }
assert input == placed.keys ⊎ dropped.keys          // checked after every stage that consumes blocks
```
`ReasonCode` is a closed enum: `SourceChrome, DuplicateOf(BlockId), InlineTocSuperseded, TitleAuthorEcho, EmptyAfterNormalization, SeparatorOnly, PromotedCopy`. A new reason needs a plan change (reviewed), preventing "dropped because convenient".

## Text layer for anchors

The concatenated `text` of a section's blocks (with `\n` between blocks) is the normalized text layer used for annotations, search snippets, and diffs. It is stored in the section index with a hash.
