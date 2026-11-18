# catalog - search design

Status: DRAFT (reconciled to PostgreSQL full-text search, D-29; Tantivy removed)

Public, Bengali-aware, ranked, safe. At under 5,000 books one PostgreSQL database is enough: no search engine, no cache layer.

## Data flow

```
catalog tables --(same transaction as publish/unpublish/metadata change)--> search_docs (tsvector row)
        ^                                                                      |
 preview asset text (PublicDocument only) --------------------------------------+--> query API
```

`search_docs` ([domain model](domain-model.md), "Search") holds one row per publicly visible book: a `tsvector` built with the `simple` configuration over text normalized by the shared `bn-text` function, plus exact keys, sort key, code and facet arrays. A row exists iff the book is visible, so unpublish removes it in the same transaction as the state change (INV-DSC-001). A rebuild command regenerates every row from tables; a `normalizer_version` mismatch triggers it. There is no event-fed index and no shadow rebuild.

## Fields and weights

| Field | Weight / use | Notes |
|---|---|---|
| title, subtitle | A | plus `title_exact_key` equality for exact-title hits |
| contributor names and aliases | B | alias expansion includes Latin transliterations; loose-key forms added for recall |
| series, category, code | C | `code` also matched by exact equality |
| summary, preview text | D | from the `PublicDocument` value only (INV-DSC-004) |

## Normalization and query

1. The query goes through the same `bn-text` version as indexing: NFC, ZWJ/ZWNJ removal, digit folding, punctuation to spaces, vowel signs always kept; recall variants use the loose key (ী/ি, ূ/ু, ণ/ন, শ ষ/স, ৎ/ত) in a separate vector weight so exact spelling ranks first.
2. Latin query: expand through the alias table; Bengali: exact and loose; mixed: union.
3. Prefix matching for the last typed token uses `to_tsquery` prefix syntax (`:*`); a `code`-shaped token is an exact code lookup; a quoted phrase uses phrase search on the title.
4. Ranking is `ts_rank_cd` over the weights, with exact-title and exact-author equality boosts; ties by `(title_sort, book_id)`.
5. Facets (category, series, writer, translator, publisher, language): AND across facets, OR within one (INV-DSC-007), via the GIN facet arrays.
6. Sort: relevance (default), title (Bengali collation sort key), newest, writer.
7. Pagination: keyset on `(rank, book_id)` or the chosen sort key, with an opaque `after` token; `q` length at most 200, limit at most 50, rate limited per IP.

Typo tolerance (edit distance) is not available in plain full-text search; it is offered only if the spike below shows it is needed and a `pg_trgm` decision is made (see open items).

## Public-safety rules

- Index inputs are `PublicDocument` only; there is no code path from the full curated text.
- Snippets are cut from summary and preview text only.
- Unpublished, archived and deleted books have no `search_docs` row; a periodic reconciler compares `search_docs` ids with published ids and alerts on drift.
- Rate limits and result window bounds: [limits](../../04-architecture/cross-cutting/limits.md).

## Quality bar (REQ-DSC-010)

Judged query set of at least 300 queries across: exact title, partial title, author only, author+title, translator, publisher, series, category, variant spellings, Latin transliteration, typo, code, mixed script, no-result. Metrics: MRR@10 >= 0.85, recall@20 >= 0.95, and zero results only when truly none. Any normalizer or weight change reruns the set in CI. Targets stay provisional until the first measurement.

## Open items (not decided here)

1. **Bengali quality spike (S-01, replaces the engine comparison).** Measure the plain `simple`-config full-text design on the judged set with real catalog data: conjunct and vowel-sign handling, prefix behaviour, transliteration recall, typo cases. Record the numbers; if the bar is missed, the options are loose-key vectors tuning, or `pg_trgm` trigram matching on normalized title and author columns (a PostgreSQL contrib extension, not a crate; needs the owner's approval, see catalog README open point 3). No suffix-stripping stemmer is used until the spike shows it helps without hurting names.
2. Whether typo tolerance is required at all at this scale (depends on the spike).
