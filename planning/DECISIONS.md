# Decision log

Status: DRAFT

Answered decisions only. Open questions live in [open-decisions](04-architecture/open-decisions.md) (no open questions at 2026-11-17); when answered they are copied here with the answer and date. ADRs record architecture choices; this log records owner decisions.

| ID | Date | Decision | Source |
|---|---|---|---|
| D-01 | 2026-11-17 | Physical/manual book inventory is **deferred to v1.1** as an optional catalog module; legacy data stays archived | owner choice (recommended option) |
| D-03 | 2026-11-17 | Ingestion stance: **obtain permission from the source; acquisition is GET-only**; locked chapters wait for an export/API or sanctioned access, never mutate the source. (The permission itself is still an open action for the owner; go-live gate G6 stays blocked until it exists.) | owner choice (recommended option); [legal](10-security/legal-source-content.md) |
| D-04 | 2026-11-17 | **Every active account may read published books by default** (default-grant policy); download, Kindle and edit remain grant-based | owner choice (recommended option); REQ-ACC-002 |
| D-17 | 2026-11-17 | Foundational Rust dependency set is approved **as one reviewed batch at the start of P1** (after version/maintenance verification); nothing is approved or installed before then | owner choice (recommended option); [dependency policy](04-architecture/dependency-policy.md) |
| D-19 | 2026-11-17 | Function-shape thresholds: **target 20 lines with hard cap 30, ≤ 3 parameters, ≤ 2 nesting levels** (lint support verified at G1) | owner choice (recommended option); [coding standards](03-correctness/coding-standards.md) |
| D-20 | 2026-11-17 | Frontend npm package set is approved **as one batch after spike S-02** | owner choice (recommended option) |
| D-21 | 2026-11-17 | **AGENTS.md is tracked in the new codebase** so rules travel with the code | owner choice (recommended option); [working agreement](00-charter/working-agreement.md) |
| D-05 | 2026-11-17 | Public preview = cover, metadata, summary, TOC and the first 3,000 characters of the first chapter (configurable per book, 0 allowed), built at publish time | owner choice (recommended option); [ADR-0007](04-architecture/adr/0007-public-preview-artifact.md) |
| D-06 | 2026-11-17 | Reader receives **chapter HTML from the server** under capabilities; the EPUB reaches the browser only with a Download grant | owner choice (recommended option); [ADR-0016](04-architecture/adr/0016-chapter-served-reader.md) |
| D-07 | 2026-11-17 | Production runs on a **single Linux host** (systemd or Compose, local PostgreSQL with WAL archiving, offsite backups) | owner choice (recommended option); [deployment topology](04-architecture/deployment-topology.md) |
| D-18 | 2026-11-17 | The OOP/SOLID-to-Rust mapping (traits, composition, enums, conformance tests; no inheritance) is accepted | owner choice (recommended option); [engineering philosophy](00-charter/engineering-philosophy.md) |
| D-08 | 2026-11-17 | UI languages: **Bengali + English**, default from `Accept-Language`, falling back to Bengali | owner choice (recommended option) |
| D-09 | 2026-11-17 | Search engines may index **metadata only**; preview text is `noindex` until D-03 permission is in hand | owner choice (recommended option) |
| D-10 | 2026-11-17 | The **demo account is kept**, strictly limited (curated read-only set, no mutations) | owner choice (recommended option) |
| D-11 | 2026-11-17 | Implement in **Rust**; microservice architecture; design must be provably sound before implementation | owner request; [ADR-0001](04-architecture/adr/0001-rust.md), [ADR-0002](04-architecture/adr/0002-independent-services.md) |
| D-12 | 2026-11-17 | Search and preview are public; reading requires an account | owner request; REQ-ACC-001/002 |
| D-13 | 2026-11-17 | Rebuild from the ground up; legacy and the earlier rewrite branch are reference only | owner request |
| D-14 | 2026-11-17 | The owner's `AGENTS.md` rules and `CLAUDE.md` working style govern this project (philosophy adopted, adapted to Rust) | owner request; [ADR-0017](04-architecture/adr/0017-engineering-philosophy.md), [engineering philosophy](00-charter/engineering-philosophy.md) |
| D-15 | 2026-11-17 | Planning is kept as living design docs: updated in the same change as behavior; decisions, conflicts and status logged in this folder | owner request; [working agreement](00-charter/working-agreement.md) |
| D-02 | 2026-11-17 | Frontend: **TypeScript + Angular + Angular Material** (answers open question D-02); Rust stays for all backend/shared code; UI types and client generated from Rust contracts | owner "OK" to recommendation; [ADR-0014](04-architecture/adr/0014-frontend-technology.md) |
| D-16 | 2026-11-17 | UI design language is **Google Material Design 3** | owner request; [design system](08-ux/design-system.md) |

Pending approval (proposed, not decided): the dependency register contents themselves (approved as a batch at P1 start, npm after S-02).
