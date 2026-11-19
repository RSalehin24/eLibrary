# ADR-0007 — Preview text is a build-time artifact, shown only to signed-in users

Status: REVIEW

Amended by D-34 (public means metadata only) and D-41 (`preview` and `read` are separate scopes).

## Context
Computing a preview by truncating full text at request time creates a leak risk (a bug exposes more than intended). Earlier text made previews public; the owner decided (D-34) that **public pages show metadata only** (browse, search, covers, summaries). Preview text and reading require sign-in.

## Decision
At publication time `catalog` derives a `PreviewArtifact` from an allow-list policy (D-05) and stores it separately. Public (unauthenticated) endpoints and the search indexer can only read metadata types (`PublicDocument`: title, contributors, series, categories, summary, cover). The preview artifact is served only to a signed-in user holding the `preview` scope. The full EPUB and the reader's reading copy are not reachable from catalog's public handlers (separate module). Public pages are server-side rendered (D-39) and may be indexed by search engines (D-09, metadata only).

## Consequences
+ Leak-proof by construction: the public path has no type that carries book text.
- Changing preview policy requires rebuilding previews (cheap; no re-ingestion).
