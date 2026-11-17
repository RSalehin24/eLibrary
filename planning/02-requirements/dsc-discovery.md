# Requirements — Discovery & search (DSC)

Status: DRAFT · Module: catalog / search ([design](../05-services/catalog/search.md))

- **REQ-DSC-001** · MUST · inv: INV-DSC-001 · verify: prop, e2e · Anonymous users can search by title, writer, translator, editor, publisher, series, category and catalog code; results are ranked and contain only Published books.
- **REQ-DSC-002** · MUST · inv: INV-DSC-002 · verify: prop, gold · Query and index text pass the same Unicode normalization (NFC, digit folding, ZWJ/ZWNJ policy, Bengali spelling-variant folding). Normalization is idempotent.
- **REQ-DSC-003** · SHOULD · inv: INV-DSC-003 · verify: gold · Latin-script queries ("humayun ahmed") match Bengali names through the alias table, and vice versa.
- **REQ-DSC-004** · MUST · inv: INV-DSC-004 · verify: model, prop, e2e · Results and snippets are produced only from public data (metadata and the Preview artifact). No full-text from non-preview sections is ever indexed in the public index.
- **REQ-DSC-005** · MUST · inv: INV-DSC-005 · verify: prop, drill · The search index is a rebuildable projection of catalog events. A full rebuild yields identical result sets; index lag p99 ≤ 30 s.
- **REQ-DSC-006** · SHOULD · inv: INV-DSC-006 · verify: unit, prop · Alphabetical sorting uses Bengali (CLDR `bn`) collation; ordering is total and stable.
- **REQ-DSC-007** · MUST · inv: INV-DSC-007 · verify: prop · Facets combine as AND across facets and OR within a facet; facet counts equal the result counts for the same filter.
- **REQ-DSC-008** · MUST · inv: INV-DSC-008 · verify: prop · Pagination is keyset-based; a page never repeats or skips a result for a fixed snapshot token.
- **REQ-DSC-009** · MUST · inv: INV-PLT-005 · verify: fuzz, e2e · Anonymous search is rate limited and query length and result window are bounded.
- **REQ-DSC-010** · MUST · inv: INV-DSC-009 · verify: gold · A versioned query set (≥ 300 judged queries) meets relevance thresholds (MRR@10 ≥ 0.85, recall@20 ≥ 0.95) and this is a CI gate for analyzer changes.
