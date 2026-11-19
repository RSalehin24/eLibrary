# catalog - search design

Status: DRAFT (PostgreSQL full-text search, D-29; public metadata only, D-34; no catalog codes, D-36)

Public, Bengali-aware, ranked, safe. Under 5,000 books one database is enough: no search engine, no cache layer.

## Data flow

```
catalog tables --(same transaction as publish / unpublish / metadata change)--> search_docs (tsvector row)
                                                                                      |
                              PublicDocument only (no preview text, no user data) ----+--> query API
```

`search_docs` ([domain model](domain-model.md)) holds one row per publicly visible book: a `tsvector` over text normalized by the shared Bengali normalizer, plus exact keys, a sort key and facet arrays. A row exists iff the book is visible, so unpublish removes it in the same transaction (INV-CAT-009). A `rebuild` command regenerates every row from the tables; a `normalizer_version` mismatch triggers it. There is no event-fed index and no shadow rebuild (REQ-CAT-013).

## Fields and weights

| Field | Weight | Notes |
|---|---|---|
| title, subtitle | A | plus `title_exact_key` equality boost |
| contributor names and aliases | B | alias expansion includes Latin transliterations; loose-key forms for recall |
| series, category | C | |
| summary | D | from `PublicDocument` only; **preview text is never indexed** (D-34, REQ-CAT-012) |

The v1 design indexed preview text at weight D; that is dropped because public pages are metadata only.

## Normalization and query (REQ-CAT-010, 011)

1. One normalizer, one version, used by index and query: NFC, ZWJ/ZWNJ policy, digit folding, punctuation to separators, vowel signs always kept in the exact key; recall variants (ী/ি, ূ/ু, ণ/ন, শ ষ/স, ৎ/ত) go to a separate loose-key vector with lower weight so exact spelling ranks first. Idempotent: `normalize(normalize(x)) = normalize(x)`. The normalizer crate is shared with ingestion so the exact keys used for duplicate matching agree.
2. Latin query: expand through the alias table; Bengali: exact and loose; mixed: union (REQ-CAT-011, SHOULD).
3. Prefix matching on the last typed token (`:*`); a quoted phrase uses phrase search on the title.
4. Ranking: `ts_rank_cd` over the weights, exact-title and exact-author boosts, ties by `(title_sort, book_id)`.
5. Facets (writer, translator, editor, publisher, series, category, language): AND across facets, OR within one, counts equal result sizes for the same filter and snapshot (REQ-CAT-015, INV-CAT-008).
6. Sort: relevance (default), title (Bengali CLDR `bn` collation sort key, REQ-CAT-014), recent. Total, stable order.
7. Pagination: keyset on `(rank, book_id)` or the chosen sort key, opaque `after` token and `snapshot` token; `q` at most 200 characters; limit default 24, max 100; per-IP rate limit at the gateway (REQ-CAT-016, 017).

Typo tolerance is not part of plain FTS; it is offered only if spike S-01 shows it is needed and a `pg_trgm` decision is made (OPEN, needs the owner's approval as a contrib extension).

## Public-safety rules

- Index inputs are `PublicDocument` values; no code path from the full text, preview text or user-private data (REQ-CAT-012). Compile-fail test and a leak canary.
- Snippets are cut from the summary only.
- Non-visible books have no `search_docs` row; a reconciler compares ids and alerts on drift.
- An update is searchable within 30 s at p99 (REQ-CAT-013; provisional, O-7).

## Quality bar (REQ-CAT-018, SHOULD per O-5)

Judged query set (initial target at least 300 queries) across exact title, partial title, author only, author plus title, translator, publisher, series, category, variant spellings, Latin transliteration, typo, mixed script, no-result. Metrics MRR@10 >= 0.85 and recall@20 >= 0.95; a normalizer or weight change reruns the set. Targets stay provisional until the first measurement. MUST or SHOULD is **OPEN (O-5)**.

## Open items (not decided here)

1. Bengali quality spike S-01 (Q-1): measure the plain `simple`-configuration design on real data; options if the bar is missed: loose-key tuning, or `pg_trgm` on normalized title and author columns (needs approval).
2. Whether typo tolerance is required at all at this scale.
