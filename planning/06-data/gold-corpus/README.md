# Gold corpus

Status: DRAFT (updated for the new ingestion pipeline and D-29 scale; kept from v1: purpose, label approach, splits)

The oracle that turns "the heuristics seem right" into a measurement for the ingestion pipeline ([ingestion](../../05-services/ingestion/README.md)) and Bengali search. It is built first (phase P0, before service code). It contains third-party book content, so it is **never committed to the repository, never put in CI images or fixtures, and never published** (CLAUDE.md; [legal](../../10-security/legal-source-content.md)). It lives on the owner's machine (or an access-controlled store outside the repository); corpus tests (`gold`) run locally and nightly where it is available, and CI without it skips them with an explicit "corpus absent" result, never a silent pass.

## Scale

The library is under 5,000 books (D-29), so a smaller labeled sample than in v1 is enough.

| Part | Size | Purpose |
|---|---|---|
| Source snapshots | 120 books | frozen raw pages as the GET-only acquisition would capture them |
| Expected curated documents | 120 | human-verified structure, labels, entities |
| Judged query set | at least 200 queries (Bengali, Latin, mixed) | search relevance (spike S-01; gate SHOULD, O-5) |
| Duplicate pairs | at least 100 labeled pairs | duplicate policy accuracy: exact normalized key plus author, category, edition; near matches go to review |
| Normalizer cases | at least 300 term pairs | Bengali normalization (vowel signs and conjuncts preserved, no collisions) |
| Annotation set | synthetic | anchor re-anchoring on a new version (D-46) |
| Canary fixtures | one per structure shape (synthetic, not the corpus) | drift tests, see [seed and fixtures](../seed-and-fixtures.md) |

The 120 books are chosen by stratum from the source site's catalog; the strata keep the shapes the pipeline must handle:

| Stratum | Books |
|---|---|
| Flat lessons | 25 |
| Nested lesson and topic | 25 |
| Sectioned (parts, volumes) | 10 |
| Multi-page table of contents | 10 |
| Single page with headings | 15 |
| Single page without usable headings (review path) | 5 |
| English or bilingual | 10 |
| Known-problem books (odd front matter, letters, disclaimers, past failures) | 15 |
| Translations with several roles, compilations | 5 |

## Label format (per book, `expected.json`, schema versioned)

```json
{ "schema": 2, "source_key": "…", "language": "bn",
  "structure": { "shape": "lesson_topic_nested",
                 "tree": [ { "title": "…", "children": [ … ], "has_own_body": true } ] },
  "front": { "title_page": true, "book_info": [ {"field":"writer","value":"…"} ],
             "dedication": "…", "front_sections": [ {"title": "…", "first_words": "…"} ] },
  "entities": { "writers": [], "translators": [], "editors": [], "publisher": "…",
                "edition": "…", "series": [], "categories": [] },
  "duplicates": { "normalized_key": "…", "outcome_vs_catalog": "new_edition" },
  "epub": { "expected_chapters": 0, "has_images": false },
  "notes": "…" }
```

Block-level labels (`block_labels.jsonl`, keyed by stable block id) cover the 40 hardest books and are used for debugging and tuning.

## What the corpus gates

| Gate | Check |
|---|---|
| Structure and entities | per-field agreement with the labels on `holdout` at or above the threshold recorded at P0 |
| Conservation and determinism | text conserved from scrape to curated document; identical input and configuration give identical EPUB bytes (REQ-NFR-012) |
| Build | every built EPUB passes the in-worker structure audit and epubcheck (D-47) |
| Duplicates | no automatic merge of a labeled near-match; labeled exact matches found |
| Search | MRR and recall on the judged queries at or above the S-01 baseline (SHOULD, O-5) |
| Normalizer | zero collisions between labeled different words |

Thresholds are set from the P0 baseline, not guessed here (OPEN: values).

## Labeling process

1. Pre-fill with the best current pipeline output; every field is actively confirmed or corrected in a small local labeling page (side-by-side source and tree).
2. Labeler (owner) plus a spot-check of 20% after a day; disagreements are tracked per field.
3. Hard cases get a written decision in the label guidelines so labeling stays consistent.
4. Labels are versioned; a label change is recorded with its reason.
5. Hold-out: 40 of the 120 books and 70 of the queries are never used while tuning rules; they run only in promotion gates.

## Splits

`dev` (80 books, 130 queries) for tuning; `holdout` (40 books, 70 queries) for gates.

## Effort

About 20 minutes per book with a good tool: roughly 40 hours for 120 books, part-time over about three weeks in P0 (smaller than v1's 70 hours because of the smaller scale).

## Storage and acquisition

Outside the repository (`.gitignore` covers `corpus/`). Snapshots are captured only by the GET-only acquisition client and for ingestion go-live and any publication only with the source owner's permission (D-03, gate G6). Labelling may start earlier for private research only (D-51): GET-only fetches, pages and labels never committed, shared or published. The residual legal risk is recorded in [legal](../../10-security/legal-source-content.md). Backups of the corpus are the owner's private matter.
