# Structure reconstruction — making it read like a printed book

Status: DRAFT

Goal: a `SectionTree` whose leaf order is exactly the book's reading order and whose nesting is exactly the author's.

## Output type

```rust
pub struct SectionTree { pub front: Vec<FrontSlot>, pub toc: TocPolicy, pub body: Vec<Node>, pub back: Vec<Node> }
pub struct Node { pub id: SectionId, pub title: DisplayText, pub kind: SectionKind, pub children: Vec<Node>,
                  pub own_blocks: Vec<BlockId>, pub source: SourceRef, pub evidence: Vec<Evidence> }
// SectionId = UUIDv5(book_id, source_key)  — stable under reorder-free rebuilds; source_key = canonical lesson/topic URL path or inferred-boundary hash
```
`toc` and `nav` are produced from this single tree by one function (INV-ING-003).

## Shapes (finite, classified once)

| Shape | Source signal | Strategy |
|---|---|---|
| `FlatLessons` | TOC of lessons, no topics | one chapter per lesson |
| `LessonTopicNested` | lessons with topic children | chapter → sections; parent kept |
| `MixedLessonsAndTopics` | some lessons have topics, some not | per-node |
| `Sectioned(<shape>)` | TOC has section headings (parts/volumes) | section headings become parent nodes without own body |
| `SinglePageHeadingSplit` | no TOC; headings in content | inference (below) |
| `SinglePageFlow` | no TOC; no usable headings | one chapter (title = book title) + review if long |
| `NoPublicBody` | nothing readable | job → Review `LockedSource`/`IncompleteSource` |

## Type A — source TOC authoritative (REQ-ING-004)

1. Collect **all** TOC pages (paginated). Merge in source order into one tree (the "unified TOC").
2. Only `/lessons/…` and `/topic/…`-type entries are chapters; `/books/…` links are cross-references and are excluded (recorded as `Dropped(SourceChrome)` with link evidence).
3. A node with both children and its own body keeps the body as the first page of that node; the node's nav/TOC entry links to that page. A node with children and **no** body links to its first descendant page but is still shown (never replaced by its children).
4. Duplicate titles at the same level are kept distinct by source URL (`SectionId` from path); display titles may be disambiguated by a deterministic suffix only when identical (" (২)"), never merged.
5. Plain-text TOCs inside the first content page are removed **only if** a linked TOC exists; recorded `Dropped(InlineTocSuperseded)`.
6. The source's own body text is never split into extra chapters. Sub-headings inside a chapter remain in-chapter headings (anchors), not new TOC nodes — unless ruleset flag `expand_subchapters` is on **and** the gold set shows it increases fidelity for that shape (default off; resolves the legacy contradiction).
7. Completeness (INV-ING-006) is checked against this tree: every leaf fetched or recorded empty-at-source.

## Type B — single page (REQ-ING-005)

Infer boundaries with scored evidence; never invent silently.

| Signal | Score | Notes |
|---|---|---|
| `h1–h3` | +3 | level maps to depth |
| `strong_only` short block (≤ 12 words, no sentence-final danda/period) | +2 | spec: counts as heading |
| Bengali boundary `. <text> .` (exact pattern) | +3 | only this exact pattern; not `..`, `...`, `\|` |
| Numeric/ordinal marker (`১।`, `অধ্যায় ২`, `প্রথম পরিচ্ছেদ`) at block start, followed by a short title or end of block | +2 | numbers inside prose are not markers |
| Isolated numeric block following a separator | +2 | |
| Block is the first after a long gap of prose and is short | +1 | |
| Block appears in a verified TOC-like list (links/anchors) | −3 | avoid TOC rows |

A boundary is accepted when score ≥ `boundary_threshold` (ruleset) **and** the resulting sequence is consistent: markers monotone (1,2,3…), segment lengths within configured ratio bounds. Inconsistent candidates → `AmbiguousStructure` review with the evidence displayed. Titles come from the heading text; untitled numbered chapters get the marker text.

## Ordering and page order

The tree is placed into the fixed page order ([builder](../builder/README.md)): Cover, Title, Book Info, Dedication, Front sections, TOC, body chapters, End sections. Front and back come from [classification](../classification/README.md); the body tree is from this stage. Chapters are never reordered by title or ordinal; **source order wins**, and a source whose numbering disagrees with its order is flagged (`AmbiguousStructure`) rather than corrected.

## Invariants checked (pure validators)

- Leaves ↔ reading positions bijection; ids unique.
- Tree depth ≤ 6; node count ≤ 5,000.
- Type A: tree ≅ source TOC (shape and normalized titles).
- Every inferred node (Type B) has ≥ 1 evidence.
- No empty leaf without a recorded reason.
