# Classification — front matter, dedication, book info, residual

Status: DRAFT

Replaces the legacy order-dependent mutate-and-decompose passes with **sequence labeling under a grammar**: each block receives exactly one label, with evidence. Conservation therefore holds by construction.

## Scope

Applies to the region before the first body chapter (front), the region after the last (back), and — for Type B books — the first segment. It never alters Type A body chapters.

## Labels (closed set)

`Title`, `Subtitle`, `AuthorLine`, `BookInfoKV`, `BookInfoLine`, `Dedication`, `FrontHeading(name)`, `FrontProse`, `Epigraph`, `Preface` (named front), `Separator`, `InlineToc`, `Chrome`, `BackHeading(name)`, `BackProse`, `Body`, `Unclassified`.

## Features per block

Position (index from start, relative to first body), kind, length, word count, `strong_only`, `ends_with_danda`, lexicon hits (role labels, publisher words, address words, edition words, month names, dedication markers, front-heading names), `key: value` shape (separators `:`, `ঃ`, `–`, `—`, `/`), digit ratio, script ratio (bn/latin), similarity to book title/author hints (from catalog hints), duplication with other blocks (normalized signature).

## Emission scores

Each label gets a score from ruleset rules (explicit, individually named `rule_id`s, each unit-tested): e.g. `dedication.marker_heading` (block text equals `উৎসর্গ` or equivalent, strong/heading) → `Dedication` +5; `kv.role_label` → `BookInfoKV` +4; `title.echo` (block equals title ± author) → `Title`/`AuthorLine` +4 and `TitleAuthorEcho` duplicate marker; `toc.list_shape` → `InlineToc` +4; `chrome.phrase` → `Chrome` +5; unknown → `FrontProse` +1 baseline.

## Grammar (transition constraints)

A region is a sequence matching (informally):

```
Front := Title? Subtitle? AuthorLine* ( BookInfo | Dedication | NamedFront | Unnamed | InlineToc | Separator )* Body
BookInfo   := ( BookInfoKV | BookInfoLine )+
Dedication := DedicationHeading Dedication{1..k}            (ends at Separator, FrontHeading, KV, or length cap 600 chars)
NamedFront := FrontHeading(name) FrontProse+                (name ∈ ruleset list OR explicitly titled in source)
Unnamed    := FrontProse+                                   (between separators)
```

Decode with dynamic programming (Viterbi over the label sequence): maximize Σ emission + Σ transition scores subject to grammar legality. Ties break deterministically (lowest label order, then earliest boundary). The decoder outputs the best sequence **and** the margin to the second best (confidence).

## Post-decode rules (from the legacy specification, now explicit)

| Rule | Behavior | Reason code if dropped |
|---|---|---|
| R1 Title-only front | A front region consisting only of title (+author) creates **no** preamble | `TitleAuthorEcho` |
| R2 KV → Book Info | Blocks labeled `BookInfoKV/Line` go to Book Info, not front sections | — |
| R3 Dedication separation | `Dedication` blocks go to the Dedication page only; mixed blocks are split at the inline marker (recorded split) | — |
| R4 Duplicate content | A block whose normalized signature (≥ 20 chars) already exists in a more specific location is dropped | `DuplicateOf(id)` |
| R5 Residual | Remaining `FrontProse` is checked for *new information* (signature not present elsewhere, ≥ N words); new KV → Book Info; new prose → unnamed front section | `EmptyAfterNormalization` if nothing new |
| R6 Naming | Titled sections keep their title on page and nav; unnamed sections show **no heading on the page**, nav label `অন্যান্য`/`Others` (+index when several) | — |
| R7 Plain-text TOC | `InlineToc` removed only if a linked TOC exists | `InlineTocSuperseded` |
| R8 Language | Labels and nav titles in the book language (INV-ING-009) | — |

## Confidence and review

Each region's confidence = min over decisions of (margin-normalized score). Below `front_confidence_threshold`, or any block left `Unclassified`, the item goes to `LowConfidenceEntity`/`AmbiguousStructure` review **with the blocks highlighted and the top-2 labelings**; the curator's choice is stored as an override input and replayed on reprocess.

## Why not a learned model first

The grammar plus lexicons is explainable, testable per rule, and works with the small gold set. A learned scorer (e.g. a linear model over the same features) may replace hand-set weights later if gold metrics justify it (ruleset change, same gates). Local inference is explicitly out of v1.
