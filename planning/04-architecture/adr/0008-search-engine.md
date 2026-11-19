# ADR-0008 — Search engine inside catalog (candidate: Tantivy)

Status: SUPERSEDED

Superseded by [ADR-0025](0025-six-services-with-gateway.md) (earlier [ADR-0020](0020-five-services-no-gateway.md)): catalog uses PostgreSQL full-text search with Bengali normalization (brief section 9); no embedded engine.

## Context
Bengali search needs custom analysis (normalization, variant folding, light suffix handling, edge n-grams, alias/transliteration), ranking, typo tolerance and facets. PostgreSQL FTS lacks Bengali analyzers; trigram helps with typos.

## Decision (pending spike S-01)
Embed a rebuildable index in `catalog` using a Rust engine with custom tokenizers (Tantivy preferred). PostgreSQL stays the source of truth; the index is a projection fed by catalog's own outbox. Fallback if the spike misses the search requirements in [cat-catalog](../../02-requirements/cat-catalog.md) thresholds: Postgres with `pg_trgm` + normalized columns + application-side ranking.

## Consequences
+ Full control over Bengali analysis; no extra service.
− Index rebuild logic and snapshot-consistent pagination are our responsibility.
