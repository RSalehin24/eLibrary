# Requirements — Catalog (CAT)

Status: DRAFT · Service: [catalog](../05-services/catalog/README.md)

- **REQ-CAT-001** · MUST · inv: INV-CAT-001 · verify: model, type · Books move through Draft → Published ⇄ Archived → Deleted only. Only Published books are publicly visible.
- **REQ-CAT-002** · MUST · inv: INV-CAT-002 · verify: db, unit · A Published book has at least one credit whose role is writer, translator or editor (compilers count as editors for this rule).
- **REQ-CAT-003** · MUST · inv: INV-CAT-003 · verify: db, prop · Each book has an immutable UUID, a stable public code, and a unique slug. A renamed slug keeps the old one as a permanent redirect.
- **REQ-CAT-004** · MUST · inv: INV-CAT-004 · verify: db, prop, e2e · Administrator edits are field-level overrides with provenance; re-ingestion never overwrites an override. Concurrent edits are detected by revision numbers (optimistic concurrency).
- **REQ-CAT-005** · MUST · inv: INV-CAT-005 · verify: db, prop, e2e · Agents (people/organizations) have aliases; names are never an identity key. Merge and split are audited, reversible, and re-point credits atomically.
- **REQ-CAT-006** · MUST · inv: INV-CAT-006 · verify: prop, gold · Work/translation/edition relationships follow the five-case duplicate policy ([entities](../05-services/ingestion/entities/README.md)). A "create as new edition" action links the new book to the existing work.
- **REQ-CAT-007** · MUST · inv: INV-CAT-007 · verify: prop, e2e · Browse pages exist for category, series (ordered), writer, translator, editor, compiler, publisher, with counts equal to the displayed result set.
- **REQ-CAT-008** · SHOULD · inv: INV-CAT-008 · verify: prop, e2e · Authorized administrators can export the current filtered list as CSV, XLSX and PDF; the export contains exactly the rows the filter returns.
- **REQ-CAT-009** · COULD · inv: INV-CAT-009 · verify: db, e2e · Physical/manual book inventory (binding, price, language) — **only if decision D-01 keeps it**; otherwise this requirement is withdrawn at gate G0.
