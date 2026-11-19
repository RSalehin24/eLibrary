# Work breakdown (epic level)

Status: DRAFT

Re-baselined 2026-11-19 for six services in Docker Compose. Kept from v1: the epic table form and the definition of done; changed: epics follow the six services (D-31), no migration or cutover epics (D-32), no demo or inventory epics (D-35; inventory deferred, D-01). Epics map to requirement families (`REQ-<PREFIX>-nnn` in [02-requirements](../02-requirements/)) and verification. Detailed tasks are created at the start of each phase, never earlier (they would rot). Efforts live in [phases](phases.md) as planning figures.

| Epic | Phase | Scope | Requirements | Key tests |
|---|---|---|---|---|
| E-01 Gold corpus and tools | P0 | labeling page, 120 books (80 dev, 40 holdout), 200 queries, 100 duplicate pairs, 300 normalizer pairs, guidelines; not blocked by the source permission (private research, GET-only, nothing committed or published, D-51) | ING (extraction, duplicates), CAT (search) | corpus self-checks |
| E-02 Spikes | P0, P1 | S-01, S-02, S-04, S-05, S-07, S-08 (P0); S-06, S-09 (P1); S-03 at P6 start | NFR, WEB, ING | spike result files |
| E-03 Workspace, Compose and CI | P1 | cargo workspace, lints (D-19), Compose skeleton for ten containers plus `migrate` and `backup`, Dockerfiles, Caddy, Postgres init (one role per service), Q1 to Q7, Q10, Q11, xtask, testkit | PLT, NFR | Q gates, INV-PLT-001 checks |
| E-04 Platform crates and contracts | P1 | config, startup checks, errors, telemetry, clock, ids, service token, outbox pull client; contract crates; codegen to the TypeScript client and service fakes | PLT | startup and contract tests |
| E-05 `domain-text` | P1 | Bengali normalizer, collation, slug | ING, CAT (matching, search) | normalizer property tests, gold normalizer cases |
| E-06 Formal models | P2 | nine planned models, three extensions, fix `access.als`, run the existing four | model invariants in [coverage](../03-correctness/formal-models/coverage.md) | Q8 |
| E-07 identity | P3 | users, invites, sessions, TOTP, reset, roles and scopes, grants, tickets, audit, profile image, host-command recovery, events | IDN | identity test plan |
| E-08 gateway | P3 | routing, authorize call, CSRF, rate limits, headers, streams, health | GWY | gateway test plan, e2e |
| E-09 web shell and auth screens | P3 | sign-in card shell, settings, users and access, M3 theme, i18n (`bn`, `en`), SSR skeleton | WEB | e2e, a11y |
| E-10 catalog core | P4 | books, versions and review workflow, metadata and history, contributors, files, internal publish endpoint, events, tombstones | CAT | catalog test plan |
| E-11 search | P4 | PostgreSQL FTS, Bengali normalization, query API, index projection from `PublicDocument` | CAT | search tests, judged queries |
| E-12 shelf, filters, downloads | P4 | My Books, saved filters (D-43), downloads, Kindle request | CAT | catalog test plan |
| E-13 web public and library | P4 | SSR public pages (metadata only), library, book detail, prototypes | WEB | e2e, a11y, SEO |
| E-14 reader service | P5 | copy build, sanitizer, package, tickets and read-once, progress, bookmarks, highlights, notes, re-anchoring, preferences, export | RDR | reader test plan |
| E-15 reader UI | P5 | whole-book renderer, modes, themes, typography, annotations UI, notes page | WEB, RDR | e2e, screen reader |
| E-16 ingestion pure crates | P1 to P6 | Block IR, structure, classification, entities, normalization, duplicate key, EPUB builder, rulesets | ING | gold gates, property tests |
| E-17 ingestion service | P6 | source adapter (GET only), mirror sync, requests, queue and worker, scrape cache, curation, duplicate review, build and epubcheck in the worker, publish saga, automation, console and SSE | ING | ingestion test plan, FI-01 to FI-04, FI-12, FI-13 |
| E-18 Import workspace UI | P6 | catalog sync, requests, review, jobs, credential status | WEB, ING | e2e |
| E-19 notify | P7 | invites, resets, Kindle with delivery status, templates, retention | NTF | notify test plan, FI-05, FI-06 |
| E-20 audit viewer and exports | P7 | audit viewer (scope OPEN, C-1), CSV export, JSON account export, erasure | IDN, CAT, RDR | unit, e2e |
| E-21 completeness | P7 | remaining requirements and screens, polish, generated report `unverified = 0` | all | traceability report |
| E-22 hardening | P8 | load, fault injection, security review, accessibility audit, monthly backup restore drill, rollback rehearsal, runbooks | NFR, PLT | FI-01 to FI-20, drills |
| E-23 launch | P9 | launch runbook, first admin, invites, first ingestion batch, first backup and restore, observation | PLT, NFR | launch checks |

## Definition of done (every epic)

0. Smallest change; owner rules respected ([philosophy](../00-charter/engineering-philosophy.md)); no unapproved dependency; any ambiguity was asked, answered and logged in `DECISIONS.md`.
1. Requirements implemented; each named verification mechanism exists and runs in CI.
2. Service docs (API, state machine, test plan) updated in the same pull requests.
3. No new `TBD`; plan check green; invariants referenced by tests by id.
4. Metrics, logs and alerts added where the epic introduces a runtime behavior.
5. Owner demo or sign-off when user-visible.
