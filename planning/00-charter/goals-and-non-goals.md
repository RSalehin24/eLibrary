# Goals and non-goals

Status: DRAFT

Basis: [new architecture](../_replan/new-architecture.md), [owner requirements](../_replan/owner-requirements.md) R-01..R-13, decisions D-26, D-29, D-31, D-32. Numeric targets marked (proposed) are assistant defaults for the owner to confirm; they are not decisions.

## Goals (measurable)

| ID | Goal | Measure | Origin |
|---|---|---|---|
| G-1 | A service can be understood, changed and tested without reading another service's code | No service crate depends on another service crate, only on shared contract crates (CI check); no service reads another's tables or volume | R-02, R-03, D-31 |
| G-2 | Access is correct by construction | Deny by default; every `/api/*` route declares a scope; a route without one fails startup; one decision point (identity) | X1-001, X1-008 |
| G-3 | Only published books are visible to readers | Property and integration tests: draft, failed-gate, archived versions never appear in reader-facing queries, tickets or files | X1-009, X1-010 |
| G-4 | No silent data loss in ingestion | Conservation check on curated documents; build gate on EPUB structure; failed build never leaves a visible book | X1-029, X1-028 |
| G-5 | Ingestion output is right (proposed) | On the gold set: structure exact match at least 98%, contributor extraction F1 at least 0.97, zero published books with an open review flag | X1-046 |
| G-6 | Reading works fast on the target scale (proposed) | Reader open to first page p95 at most 2 s for a 5 MB book; catalog search p95 at most 300 ms at 50 users | D-29 |
| G-7 | Recoverable | Monthly backups (D-33) of every database and file volume, copied off the host; restore drill passes; RPO up to 30 days, RTO at most 4 h | X1-080, X1-083 |
| G-8 | Accessible and responsive | WCAG AA in light and dark on every screen; layouts verified on four window classes | R-06..R-09, D-25, D-26 |
| G-9 | Operable by one person | One Compose stack, per-container memory limits, secrets as files, rolling restart per service, health endpoints, structured logs | D-22, D-24 |
| G-10 | Honest about content protection | Docs and UI state that the reader is not DRM; opens are audited and rate-limited | D-28 |

## Non-goals

- Public sign-up (accounts are by invitation only).
- DRM or technical prevention of copying by an entitled reader (D-28 limit).
- PWA, offline reading or native apps.
- Social features (sharing, comments, follows, recommendations) and payments.
- Migrating any legacy data: users, books, annotations (D-32). Old data stays in `archive/`.
- XLSX and PDF export (CSV only; they would need new dependencies).
- Redis, Celery or any message broker; a separate search engine or cache layer (D-29).
- Manual EPUB or file upload in v1: intake is the scrape pipeline only (D-42); manual metadata edit stays.
- Physical (manual) book inventory in v1 (deferred to v1.1, D-01).
- Acquisition that writes to the source site, or evades its protections (D-03).
- Proving the scraped website behaves: misbehaviour is detected and quarantined.
- Microservices for their own sake: a service exists only where there is an ownership or failure boundary.
- Zero-defect claims; see claims and limits in `03-correctness`.
