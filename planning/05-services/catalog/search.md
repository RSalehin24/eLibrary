# catalog — search design

Status: DRAFT

The hardest user-facing feature after reading. Public, Bengali-aware, ranked, safe.

## Data flow

```
catalog tables ──outbox──► IndexBuilder ──► index (Tantivy, derived)  ◄── query API ◄── gateway
                                  ▲
 content: PublicDocument (preview) ┘   (only type accepted: INV-DSC-004)
```

Full rebuild = replay of `Book*`/`Agent*` events + a preview fetch per book. Incremental update on each event. The index stores a `snapshot_id` (monotonic version) used by keyset pagination.

## Documents and fields

| Field | Analyzer | Boost | Notes |
|---|---|---|---|
| `title` | bn-text + edge-ngram(2..15) | 6 | exact-key field `title_exact` boost 10 |
| `title_fuzzy` | fuzzy-key tokens | 3 | folds spelling variants |
| `agent_names` (writer) | bn-text + alias expansion | 5 | aliases include Latin transliterations |
| `agent_names` (other roles) | same | 2 | translator, editor, compiler, publisher |
| `series`, `category` | bn-text | 2 | facets as well |
| `code` | keyword | 10 | exact |
| `summary`, `preview_text` | bn-text | 1 | from PublicDocument only |

## Analyzer chain (`bn-text`)

NFC → NFKC key → case-fold → digit fold → ZWJ/ZWNJ strip (key only) → tokenizer (Unicode word boundaries + Bengali conjunct safe) → light suffix stripping (small, versioned list: -র, -ের, -কে, -দের, -গুলো, -টি, -টা, -য়, -তে… only when the stem ≥ 2 graphemes) → fuzzy folding (separate field).

Why light suffix stripping, not a stemmer: a wrong stem hurts precision on proper names (authors, titles); names are matched on the unstripped field first.

## Query processing

1. Normalize query with the same `domain-text` version.
2. Detect script: Latin → expand via alias table; Bengali → both exact and fuzzy fields; mixed → union.
3. Intent hints: `code`-shaped token → exact code; quoted phrase → phrase query on title.
4. Compose: `should(exact title, prefix title, fuzzy title, agent match, series/category match, preview match)` with boosts; typo tolerance edit distance ≤ 1 for tokens ≥ 4 graphemes, ≤ 2 for ≥ 8.
5. Facets (category, series, writer, translator, publisher, language): AND across, OR within (INV-DSC-007).
6. Sort: relevance (default), title (Bengali collation), newest, writer.
7. Pagination: keyset on `(score, doc_id)` under `snapshot_id`; the response returns a `next` token bound to the snapshot; an expired snapshot returns a typed `snapshot_expired` and the client restarts (INV-DSC-008).

## Public-safety rules

- Index inputs are `PublicDocument` only; there is no code path from `FullDocument`.
- Snippets are cut from preview text and summary only.
- Unpublished or archived books are removed on the event (INV-DSC-001), and an hourly reconciler compares index ids to `Published` ids and alerts on drift.
- Rate limits and result window bounds ([limits](../../04-architecture/cross-cutting/limits.md)).

## Quality bar (REQ-DSC-010)

Judged query set ≥ 300 queries across: exact title, partial title, author only, author+title, translator, publisher, series, category,
variant spellings, Latin transliteration, typo, code, mixed script, no-result. Metrics: MRR@10 ≥ 0.85, recall@20 ≥ 0.95, no-result precision (zero results only when truly none). Any analyzer or normalizer change reruns the set in CI (Q9).

## Spike S-01 (before ADR-0008 is accepted)

Compare Tantivy analyzers vs PostgreSQL `pg_trgm` + normalized columns on the judged set using real catalog data; decide; record numbers in the ADR.
