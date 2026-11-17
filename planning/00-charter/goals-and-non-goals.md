# Goals and non-goals

Status: DRAFT

## Goals (measurable)

| ID | Goal | Measure |
|---|---|---|
| G-1 | A service can be understood, changed and tested without reading another service's code | No crate depends on another service crate; only on `contracts-*` crates (checked in CI) |
| G-2 | No silent data loss in ingestion | Conservation invariant holds on 100% of gold-corpus books and in property tests |
| G-3 | Ingestion output is right | On the held-out gold set: structure exact-match ≥ 98%, author/translator/publisher F1 ≥ 0.97, zero published books with an unresolved review flag |
| G-4 | Public pages are fast | p95 TTFB ≤ 300 ms (search, book page) at 50 rps on the target host |
| G-5 | Authorization is correct by construction | Access model checked exhaustively (Alloy) and the Rust `decide` function passes the same cases via property tests |
| G-6 | Recoverable | RPO ≤ 15 min, RTO ≤ 1 h, restore drill passes quarterly |
| G-7 | Migration loses nothing | Reconciliation report with zero unexplained differences |
| G-8 | Accessible | WCAG 2.2 AA on all public and reader pages (automated + manual audit) |

## Non-goals

- Proving the scraped website behaves. We *detect and quarantine* misbehaviour.
- Proving UX quality. UX is verified by review checklists and usability sessions, not theorems.
- Microservices for their own sake. Services exist where an ownership/failure/scaling
  boundary exists ([service catalog](../04-architecture/service-catalog.md)).
- Zero defects claims. See [claims and limits](../03-correctness/claims-and-limits.md).
