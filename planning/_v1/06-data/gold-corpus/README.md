# Gold corpus

Status: DRAFT

The oracle that turns "the heuristics seem right" into a measurement. It is the single highest-value asset in the project and is built **first** (phase P0, before service code).

## Contents

| Part | Size (initial) | Purpose |
|---|---|---|
| Source snapshots | 200 books | frozen raw pages (what acquisition would capture) |
| Expected canonical documents | 200 | human-verified structure, labels, entities |
| Judged query set | ≥ 300 queries | search relevance (REQ-DSC-010) |
| Duplicate pairs | ≥ 150 labeled pairs | five-case policy accuracy |
| Annotation mutation set | synthetic | anchor re-anchoring tests |
| Canary fixtures | one per structure shape | acquisition/drift tests |

## Sampling (stratified; sample from the ~1,800 existing books and failures)

| Stratum | Books | Why |
|---|---|---|
| Type A flat lessons | 40 | common case |
| Type A nested (lesson/topic) | 40 | nesting, parents with bodies |
| Type A with section headings (parts/volumes) | 15 | `Sectioned` |
| Type A paginated TOC (multi-page) | 15 | completeness |
| Mixed lessons/topics | 10 | per-node |
| Type B single page (headings) | 25 | inference |
| Type B no usable headings | 5 | review path |
| English / bilingual books | 15 | language labels |
| Known-problem books (past failures, odd front matter, letters, disclaimers) | 25 | edge cases (include the legacy `last_chapter_title` book and kabitasamagra-type) |
| Translations with several roles, compilations | 10 | role parsing |

## Label format (per book, `expected.json`, schema versioned)

```json
{ "schema": 1, "source_key": "…", "language": "bn",
  "structure": { "shape": "lesson_topic_nested",
                 "tree": [ { "title": "…", "children": [ … ], "has_own_body": true } ] },
  "front": { "title_page": true, "book_info": [ {"field":"writer","value":"…"}, … ],
             "dedication": "…" | null,
             "front_sections": [ {"title": "ভূমিকা" | null, "first_words": "…"} ] },
  "back": [ … ],
  "entities": { "writers": [..], "translators": [..], "editors": [..], "publisher": "…",
                "edition": "…", "first_published": "…", "series": [..], "categories": [..] },
  "duplicates": { "work_key": "…", "outcome_vs_catalog": "NewEdition" },
  "notes": "…" }
```
Block-level labels (which block is dedication/book info) are stored as `block_labels.jsonl` keyed by stable `BlockId` for the 60 hardest books (used to train/tune weights and debug).

## Labeling process

1. Pre-fill with the best current output (legacy pipeline) to speed labeling; **every field must be actively confirmed or corrected** in a labeling tool (a small web page generated from the snapshot with side-by-side source and tree).
2. Two-pass: labeler (owner) + spot-check of 20% by a second review after a day (self-review with fresh eyes if no second person; discrepancies tracked as `kappa`-style agreement on fields).
3. Hard cases get a written decision in `docs/label-guidelines.md` so labeling is consistent (e.g. "is 'প্রকাশক:' in the middle of a letter a publisher?").
4. Labels are versioned; a label change is a commit with justification.
5. Hold-out: 60 of the 200 are **never** used while tuning rules; they run only in promotion gates.

## Splits

`dev` (140) for rule tuning · `holdout` (60) for gates. The judged queries split 200/100 likewise.

## Effort estimate

~20 minutes/book for confirm/correct with a good tool → ≈ 70 hours for 200 books. This is a deliberate investment: it replaces the open-ended heuristic whack-a-mole and gives the Rust port a target. Phase P0 budgets four weeks part-time.

## Storage

Snapshots and labels in `corpus/` (git-lfs or a separate repo); contain third-party content, so **access-controlled and never published** (see [legal](../../10-security/legal-source-content.md)).
