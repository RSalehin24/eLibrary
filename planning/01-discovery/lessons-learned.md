# Lessons learned

Status: DRAFT

Source: the [X1 issues register](../_replan/analysis/X1-issues-register.md) (136 issues, top-25 boundary list in its section 2) and [new architecture](../_replan/new-architecture.md) section 7. The earlier rewrite branch `reyan-new-version` is reference only; its lessons are kept from v1 at the end.

## Top defects and the rule that answers each

| # | Legacy defect | X1 | Design rule (new architecture section 7) | Where it is enforced |
|---|---|---|---|---|
| 1 | Shelf made any user "owner" and bypassed all gates; wildcard roles; AllowAny default | X1-001, X1-008 | Deny by default, scope declared per route, ownership never grants access | Identity decision point; startup check of route scopes |
| 2 | Draft, rejected, failed and deleted books visible and readable | X1-009, X1-010 | Only `published` versions are visible; entitlement includes publication state | Catalog reader-facing queries; reader open |
| 3 | Reader token in URL, token-only content routes, no revocation | X1-003 | Header or body ticket, 15 min, bound to user and version, revocable by grant version | Reader tickets |
| 4 | `/media/` served without auth | X1-011 | Files never served by Caddy or gateway; services stream after a check | Catalog and reader file routes |
| 5 | Job engine on Redis pub/sub: lost messages, double runs, success reported for failures | X1-065..X1-067, X1-031 | PostgreSQL queue with leases and typed outcomes; status is separate from outcome | Ingestion jobs table |
| 6 | Pipeline ran inside the HTTP request when dispatch failed | X1-067 | No inline execution anywhere | Ingestion API only enqueues |
| 7 | Retry chosen by error text; pause only between big steps | X1-068 | Typed errors; cancel flag checked per page | Ingestion worker |
| 8 | Whole book stored in several rows, four copies of content | X1-035, X1-030 | One authoritative curated document; derived artifacts regenerable | Ingestion and catalog data ownership |
| 9 | Scraper posted "mark complete" to the source site | X1-012 | Acquisition is GET-only (D-03) | Ingestion fetcher (no POST method exists) |
| 10 | Autoescape off, unsanitized HTML, images and fonts missing from EPUB | X1-004, X1-047 | Escaping on, allow-list sanitize, package images and fonts, audit gate | Ingestion build; reader sanitizer |
| 11 | Substring title matching; Bengali word lists without vowel signs | X1-046, X1-049 | Exact normalized key plus author, category, edition | Ingestion curate |
| 12 | Dark mode broken for OS preference; hard-coded colours; ten breakpoints | X1 section 1.6 | M3 tokens, `prefers-color-scheme` plus toggle, four window classes | Web design system |
| 13 | No backups, no limits, secrets printed on deploy, deploy does down then up | X1-080, X1-083, X1-013, X1-002 | Backups with restore drill, resource limits, secrets via files, rolling restart per service | Platform and operations |
| 14 | Two parallel pipelines, duplicated mirror, job and request concepts | X1-106, X1-030 | One pipeline in ingestion; each service owns its state; no dual-written mirrors or triggers | Service data ownership |
| 15 | Destructive re-scrape overwrote published content; non-atomic persistence | X1-027, X1-028 | New builds are candidates; publish is one transaction; previous version kept until the next is published | Catalog versions |
| 16 | Sync re-run overwrote workflow state; empty list resolved everything | X1-024, X1-026 | Mirror and workflow state stored separately; empty input is a no-op | Ingestion mirror |
| 17 | Test backdoor in production control flow; shared demo credentials | X1-005, X1-007 | Test seams by substitution only; no demo account (D-35) | Identity, all services |
| 18 | Anonymous intake endpoints guarded by UUID secrecy | X1-006 | Invite-only: every intake route needs a session and `operate` | Gateway and ingestion |

## Process lessons (kept from v1)

1. Boundaries by folder are not boundaries: free imports in one database produced cycles. Services own their data and share only contracts.
2. State copied for the UI becomes a second source of truth: read models are derived and rebuildable.
3. Heuristics without an oracle only grow: every normalization or matching rule needs a gold-set metric.
4. Silent drops hide bugs: nothing is discarded without a recorded reason.
5. Percentage tolerance is not completeness: completeness is a gate with named causes.
6. Never accept scope explosion in one branch (`reyan-new-version`: framework swap, PWA, broker, engine extraction in one 124k-line change that never passed UX acceptance). One phase delivers one thing a person can use; gates block progress.
7. Handover documents must not be longer than the decisions they record; docs stay short and decisions are logged.
8. Good ideas from that branch: a service ownership table, no cross-service foreign keys, opaque ids, a private versioned contract, and reader or engine failure not breaking browsing.
