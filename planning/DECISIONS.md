# Decision log

Status: DRAFT

Answered decisions only. Open questions live in [open-decisions](04-architecture/open-decisions.md) (open ids: D-05…D-10, D-17…D-21); when answered they are copied here with the answer and date. ADRs record architecture choices; this log records owner decisions.

| ID | Date | Decision | Source |
|---|---|---|---|
| D-01 | 2026-11-17 | Physical/manual book inventory is **deferred to v1.1** as an optional catalog module; legacy data stays archived | owner choice (recommended option) |
| D-03 | 2026-11-17 | Ingestion stance: **obtain permission from the source; acquisition is GET-only**; locked chapters wait for an export/API or sanctioned access, never mutate the source. (The permission itself is still an open action for the owner; go-live gate G6 stays blocked until it exists.) | owner choice (recommended option); [legal](10-security/legal-source-content.md) |
| D-04 | 2026-11-17 | **Every active account may read published books by default** (default-grant policy); download, Kindle and edit remain grant-based | owner choice (recommended option); REQ-ACC-002 |
| D-11 | 2026-11-17 | Implement in **Rust**; microservice architecture; design must be provably sound before implementation | owner request; [ADR-0001](04-architecture/adr/0001-rust.md), [ADR-0002](04-architecture/adr/0002-independent-services.md) |
| D-12 | 2026-11-17 | Search and preview are public; reading requires an account | owner request; REQ-ACC-001/002 |
| D-13 | 2026-11-17 | Rebuild from the ground up; legacy and the earlier rewrite branch are reference only | owner request |
| D-14 | 2026-11-17 | The owner's `AGENTS.md` rules and `CLAUDE.md` working style govern this project (philosophy adopted, adapted to Rust) | owner request; [ADR-0017](04-architecture/adr/0017-engineering-philosophy.md), [engineering philosophy](00-charter/engineering-philosophy.md) |
| D-15 | 2026-11-17 | Planning is kept as living design docs: updated in the same change as behavior; decisions, conflicts and status logged in this folder | owner request; [working agreement](00-charter/working-agreement.md) |
| D-02 | 2026-11-17 | Frontend: **TypeScript + Angular + Angular Material** (answers open question D-02); Rust stays for all backend/shared code; UI types and client generated from Rust contracts | owner "OK" to recommendation; [ADR-0014](04-architecture/adr/0014-frontend-technology.md) |
| D-16 | 2026-11-17 | UI design language is **Google Material Design 3** | owner request; [design system](08-ux/design-system.md) |

Pending approval (proposed, not decided): dependency register ([policy](04-architecture/dependency-policy.md)), adaptations I-01…I-04.
