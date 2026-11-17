# Decision log

Status: DRAFT

Answered decisions only. Open questions live in [open-decisions](04-architecture/open-decisions.md) (ids D-01…D-10); when answered they are copied here with the answer and date. ADRs record architecture choices; this log records owner decisions.

| ID | Date | Decision | Source |
|---|---|---|---|
| D-11 | 2026-11-17 | Implement in **Rust**; microservice architecture; design must be provably sound before implementation | owner request; [ADR-0001](04-architecture/adr/0001-rust.md), [ADR-0002](04-architecture/adr/0002-independent-services.md) |
| D-12 | 2026-11-17 | Search and preview are public; reading requires an account | owner request; REQ-ACC-001/002 |
| D-13 | 2026-11-17 | Rebuild from the ground up; legacy and the earlier rewrite branch are reference only | owner request |
| D-14 | 2026-11-17 | The owner's `AGENTS.md` rules and `CLAUDE.md` working style govern this project (philosophy adopted, adapted to Rust) | owner request; [ADR-0017](04-architecture/adr/0017-engineering-philosophy.md), [engineering philosophy](00-charter/engineering-philosophy.md) |
| D-15 | 2026-11-17 | Planning is kept as living design docs: updated in the same change as behavior; decisions, conflicts and status logged in this folder | owner request; [working agreement](00-charter/working-agreement.md) |

Pending approval (proposed, not decided): dependency register ([policy](04-architecture/dependency-policy.md)), adaptations I-01…I-04.
