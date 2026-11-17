# ADR-0007 — Public preview is a build-time artifact

Status: REVIEW

## Context
Search and preview become public. Computing a preview by truncating full text at request time creates a leak risk (a bug exposes more than intended) and couples public traffic to protected data.

## Decision
At build time `content` derives a `PreviewArtifact` from an allow-list policy (D-05) and stores it separately. Public endpoints and the search indexer can only read `PreviewArtifact`/`PublicDocument` types. The full document store is not reachable from public handlers (separate module, separate credentials where possible).

## Consequences
+ Leak-proof by construction (INV-CON-003, INV-DSC-004).
− Changing preview policy requires rebuilding previews (cheap; no re-ingestion).
