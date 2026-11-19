# Flow: automatic publish

Status: DRAFT

Actors: no human for the normal path (D-49). An operator (`operate`) acts only on holds in the Import workspace; a user with `manage_catalog` (operator or admin, D-45) edits, unpublishes or deletes afterwards. Requirements: REQ-ING-029, 036; REQ-CAT-001, 004, 006, 021, 024. This flow replaces the former publish-approval flow; there is no approval surface and no In review state.

Normal path:
1. A request's build passes every gate: curated validation, structure audit, epubcheck with 0 errors in the worker (D-47) and the exact-key duplicate rule (or a duplicate review the operator already resolved as new or new edition).
2. Ingestion calls catalog `POST /internal/books/{id}/versions` with the gate-passing artifacts. Catalog publishes the version in the same transaction (atomic switch of the current version); the book is visible in the Library, the reader builds its copy, and the previous version's files are kept until this one is published.
3. What an operator sees: the request in the Import workspace moves to Published with a link to the book (`/books/:slug`); the request detail lists the gate results. No step waits for a person and no badge counts pending approvals.

Holds (operator acts in the Import workspace, see [import end to end](import-end-to-end.md) and [review a duplicate](review-duplicate.md)):
- A failed gate or an unclear duplicate never reaches catalog. The request stays in `needs_review` (review items or duplicate review) or `failed`, with the reason and the gate results on its detail page. The operator resolves, retries or discards it.
- Catalog refuses the publish call (hash mismatch, missing credit, slug taken): the request goes to `needs_review` with a `CatalogRejected` item naming the cause.

After publication (manual, `manage_catalog`, in [Catalog management](../screens/catalog-management.md) and [Book detail](../screens/book-detail.md), tab Metadata):
- Edit metadata with `If-Match: <revision>`; a stale revision shows the server value for a manual decision, never a silent merge. A published book keeps at least one writer, translator, editor or compiler credit (`no_credit` inline error). Every edit is audited.
- Unpublish (`POST /manage/books/{id}/archive`, confirm, readers lose access at once, reversible by restore) and Delete (soft delete, confirm naming the book, scope **OPEN O-4**); both are audited.
- A reprocessed build goes through the same gates and, if they pass, replaces the published version automatically; annotations are re-anchored by the reader (D-46).

Branches: `invalid_transition` (someone else unpublished first): current state shown with Refresh. A defect that passed every gate is public until someone unpublishes it (risk R-24); the gold-corpus gate and the audit trail are the mitigations.
