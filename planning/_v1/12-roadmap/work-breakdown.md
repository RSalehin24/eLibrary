# Work breakdown (epic level)

Status: DRAFT

Epics map to requirements and verification. Detailed tasks are created at the start of each phase, never earlier (they would rot).

| Epic | Phase | Scope | Requirements | Key tests |
|---|---|---|---|---|
| E-01 Gold corpus & tools | P0 | labeling tool, 200 books, queries, pairs, guidelines | ING-011, DSC-010, CAT-006 | corpus self-checks |
| E-02 Workspace & CI | P1 | layout, lints, Q1–Q7, xtask | PLT-001/002/004/005 | Q-gates |
| E-03 `domain-text` | P1 | normalizer, keys, collation, slug | DSC-002/006 | TST-DSC-001/007 |
| E-04 Formal models | P2 | all models checked | ACC/ING/PLT model INVs | Q8 |
| E-05 identity | P3 | accounts, links, sessions, TOTP, throttle | IDN-* | TST-IDN-* |
| E-06 access | P3 | decide, grants, capabilities, openings | ACC-* | TST-ACC-* |
| E-07 gateway | P3 | routing, CSRF, rate limit, assertions, headers | GWY-* | e2e |
| E-08 catalog core | P4 | books, agents, taxonomy, overrides, redirects | CAT-* | TST-CAT-* |
| E-09 search | P4 | analyzer, index projection, query API | DSC-* | TST-DSC-* |
| E-10 content (public) | P4 | preview/cover, store, artifact sets | CON-001/002/003/008/009 | TST-CON-* |
| E-11 web public | P4 | pages, design system, SEO, i18n | WEB-* | e2e, a11y |
| E-12 content (protected) | P5 | sections, EPUB, ranges | CON-004/005/006/007 | TST-CON-* |
| E-13 library | P5 | progress, sessions, annotations, shelf, filters | LIB-* | TST-LIB-* |
| E-14 reader | P5 | ReaderHost impl, settings, annotations UI | WEB-001/003/004 | e2e, SR |
| E-15 ingestion pure crates | P1→P6 | Block IR, structure, classification, entities, builders, rulesets | ING-001…009, 011, 015 | TST-ING-002…010, 016 |
| E-16 ingestion service | P6 | acquisition, orchestration, saga, review, reprocess | ING-006, 010, 012…014, 016 | TST-ING-001, 007, 011, 013, 015, 017, 018 |
| E-17 admin UI | P3→P7 | accounts/access, catalog editor, Sources/Jobs/Review, audit | WEB-008 | e2e |
| E-18 notify | P7 | mail, Kindle, templates | NTF-* | TST-NTF-* |
| E-19 exports | P7 | CSV/XLSX/PDF | CAT-008 | TST-CAT-007 |
| E-20 inventory (D-01) | P7 or later | physical books | CAT-009 | db/e2e |
| E-21 migration | P8 | ETL, reconciliation, rehearsals | MIG-* | drills |
| E-22 hardening | P8 | load, FI, security, a11y audit, restore drill | PLT-007/008 | FI-*, drills |
| E-23 cutover | P9 | runbook execution | MIG-004 | cutover checks |

## Definition of done (every epic)

0. Smallest change; owner rules respected ([philosophy](../00-charter/engineering-philosophy.md)); no unapproved dependency; any ambiguity was asked, answered and logged in `DECISIONS.md`.
1. Requirements implemented; each named verification mechanism exists and runs in CI.
2. Service docs (API, state machine, test plan) updated in the same pull requests.
3. No new `TBD`; plan check green; invariants referenced by tests by id.
4. Metrics/logs/alerts added where the epic introduces a runtime behavior.
5. Owner demo or sign-off when user-visible.
