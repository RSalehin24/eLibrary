# Risk register

Status: DRAFT

Likelihood/Impact: L/M/H. Owner is the user unless stated.

| ID | Risk | L | I | Mitigation | Trigger / early signal |
|---|---|---|---|---|---|
| R-01 | Source content not licensed for republication (D-03) | M | H | Decision before ingestion go-live; keep source attribution; ability to unpublish per source | Unanswered at G0 |
| R-02 | Source site changes markup | H | M | Drift detector, canary per structure type, halt-on-drift | Canary failing |
| R-03 | Bengali extraction quality below targets | M | H | Gold corpus first; rules + lexicons; review queue; no auto-publish below threshold | Gold F1 < target at G6 |
| R-04 | Rust rewrite of 20k lines of heuristics takes too long | H | H | Port by stage with the Python pipeline as oracle; pure library crates; scope stage-by-stage | Stage > 2× estimate |
| R-05 | Formal models diverge from code | M | M | Model-based tests; invariant register ties code to model; review on change | Model-based test failures |
| R-06 | Search relevance for Bengali insufficient | M | M | Spike S-01; judged query set; fallback to Postgres trigram | MRR < 0.85 |
| R-07 | Angular Material lacks needed M3 components / Angular churn / second toolchain burden | M | M | Spike S-02 component audit; compose from CDK + tokens; pin one Angular major and upgrade deliberately; reader behind `ReaderHost`; generated client keeps types in sync | S-02 gaps; upgrade breaks visual snapshots |
| R-15 | npm dependency tree conflicts with "minimal dependencies" rule | M | M | register + approval; lockfile discipline; `npm audit` nightly; prefer Angular/CDK built-ins over extra packages | register growth beyond approved set |
| R-08 | Operational complexity of many services for one developer | M | M | Single-binary dev mode; shared platform kit; same deploy script; consolidate services if toil > threshold | Deploy > 30 min or on-call load |
| R-09 | Data migration loses/corrupts data | L | H | Idempotent steps, reconciliation, rehearsals, rollback | Any unexplained diff |
| R-10 | Scope creep (repeat of the rewrite branch) | H | H | Gates, non-goals, one deliverable per phase, user sign-off | Phase exceeds budget by 50% |
| R-11 | TLA+/Alloy tooling not usable in CI | M | L | Spike S-04; run locally with committed results as fallback | Spike fails |
| R-12 | Public search abused (scraping/DoS) | M | M | Rate limits, caching, query bounds, bot rules | Traffic spikes |
| R-13 | Security incident (credential leak, session theft) | L | H | Threat model, short-lived capabilities, MFA, secret rotation runbook | Audit finding |
| R-14 | Specification wrong (builds the wrong thing) | M | H | Sign-offs at G0 and G4, prototypes of public pages before backend depth | User rejects prototype |
